from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


POSTHOG_HOST = "https://us.posthog.com"
TIMEZONE = "America/Santiago"
DEFAULT_LIMIT = 10_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export events and sessions from PostHog. "
            "If dates are not provided, the script detects and downloads the available history."
        )
    )
    parser.add_argument("--project-id", default=os.getenv("POSTHOG_PROJECT_ID"))
    parser.add_argument("--api-key", default=os.getenv("POSTHOG_API_KEY"))
    parser.add_argument(
        "--legacy-script",
        default=None,
        help=(
            "Optional path to an old posthog.py file used only to read project_id/API_KEY "
            "when environment variables are not configured. Do not commit that legacy file."
        ),
    )
    parser.add_argument("--start", default=None, help="Optional start date: YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Optional end date: YYYY-MM-DD")
    parser.add_argument("--chunk-days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def read_legacy_credentials(path: str | None) -> tuple[str | None, str | None]:
    if not path:
        return None, None

    text = Path(path).read_text(encoding="utf-8")
    project_match = re.search(r"project_id\s*=\s*['\"]([^'\"]+)['\"]", text)
    key_match = re.search(r"API_KEY\s*=\s*['\"]([^'\"]+)['\"]", text)
    project_id = project_match.group(1) if project_match else None
    api_key = key_match.group(1) if key_match else None
    return project_id, api_key


def hogql(project_id: str, api_key: str, query: str, max_retries: int = 4) -> dict:
    url = f"{POSTHOG_HOST}/api/projects/{project_id}/query/"
    payload = json.dumps({"query": {"kind": "HogQLQuery", "query": query}}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < max_retries - 1:
                wait_seconds = int(exc.headers.get("Retry-After", 30))
                print(f"Rate limit. Waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"PostHog HTTP {exc.code}: {body}") from exc

    raise RuntimeError("PostHog query could not be completed.")


def parse_posthog_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def detect_available_range(project_id: str, api_key: str) -> tuple[date, date]:
    query = """SELECT
    min(timestamp) AS min_event,
    max(timestamp) AS max_event,
    (SELECT min(`$start_timestamp`) FROM sessions) AS min_session,
    (SELECT max(`$start_timestamp`) FROM sessions) AS max_session
FROM events"""
    response = hogql(project_id, api_key, query)
    row = response["results"][0]

    dates = [parse_posthog_date(value) for value in row if value]
    if not dates:
        raise RuntimeError("PostHog did not return available dates.")

    return min(dates), max(dates)


def date_chunks(start_date: date, end_date: date, chunk_days: int) -> Iterable[tuple[date, date]]:
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def write_csv(path: Path, columns: list[str], rows: list[list], write_header: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(columns)
        writer.writerows(rows)


def query_events(start_str: str, end_str: str, limit: int) -> str:
    return f"""SELECT
    distinct_id,
    event,
    properties.screen AS screen,
    properties.sub_screen AS sub_screen,
    properties.action AS action,
    formatDateTime(toTimeZone(timestamp, '{TIMEZONE}'), '%d-%m-%Y %H:%i:%s') AS datetime,
    timestamp
FROM events
WHERE timestamp >= toDateTime('{start_str}', '{TIMEZONE}')
  AND timestamp <= toDateTime('{end_str}', '{TIMEZONE}')
ORDER BY timestamp DESC
LIMIT {limit}"""


def query_sessions(start_str: str, end_str: str, limit: int) -> str:
    return f"""SELECT
    distinct_id,
    formatDateTime(toTimeZone(`$start_timestamp`, '{TIMEZONE}'), '%d-%m-%Y %H:%i:%s') AS start,
    formatDateTime(toTimeZone(`$end_timestamp`, '{TIMEZONE}'), '%d-%m-%Y %H:%i:%s') AS end,
    formatDateTime(toTimeZone(max_inserted_at, '{TIMEZONE}'), '%d-%m-%Y %H:%i:%s') AS max_insert,
    `$session_duration` AS duration,
    `$start_timestamp`
FROM sessions
WHERE `$start_timestamp` >= toDateTime('{start_str}', '{TIMEZONE}')
  AND `$start_timestamp` <= toDateTime('{end_str}', '{TIMEZONE}')
ORDER BY `$start_timestamp` DESC
LIMIT {limit}"""


def run_query_for_kind(
    project_id: str,
    api_key: str,
    kind: str,
    start_date: date,
    end_date: date,
    limit: int,
) -> tuple[list[str], list[list]]:
    start_str = f"{start_date:%Y-%m-%d} 00:00:00"
    end_str = f"{end_date:%Y-%m-%d} 23:59:59"
    query = query_events(start_str, end_str, limit) if kind == "events" else query_sessions(start_str, end_str, limit)
    response = hogql(project_id, api_key, query)
    return response.get("columns", []), response.get("results", [])


def export_kind(
    project_id: str,
    api_key: str,
    kind: str,
    start_date: date,
    end_date: date,
    limit: int,
    output_path: Path,
    sleep: float,
    write_header_state: dict[str, bool],
) -> int:
    columns, rows = run_query_for_kind(project_id, api_key, kind, start_date, end_date, limit)

    if len(rows) >= limit and start_date < end_date:
        midpoint = start_date + (end_date - start_date) // 2
        left = export_kind(project_id, api_key, kind, start_date, midpoint, limit, output_path, sleep, write_header_state)
        right = export_kind(project_id, api_key, kind, midpoint + timedelta(days=1), end_date, limit, output_path, sleep, write_header_state)
        return left + right

    if len(rows) >= limit and start_date == end_date:
        print(
            f"  Warning: {kind} reached LIMIT {limit} on {start_date:%Y-%m-%d}. "
            "That day may be truncated and should be reviewed with hourly ranges."
        )

    if rows:
        write_csv(output_path, columns, rows, write_header_state[kind])
        write_header_state[kind] = False

    time.sleep(sleep)
    return len(rows)


def export_range(
    project_id: str,
    api_key: str,
    start_date: date,
    end_date: date,
    chunk_days: int,
    limit: int,
    output_dir: Path,
    sleep: float,
) -> tuple[Path, Path, int, int]:
    stamp = f"{start_date:%Y_%m_%d}_a_{end_date:%Y_%m_%d}"
    events_path = output_dir / f"posthog_events_{stamp}.csv"
    sessions_path = output_dir / f"posthog_sessions_{stamp}.csv"
    partial_events_path = output_dir / f".partial_posthog_events_{stamp}.csv"
    partial_sessions_path = output_dir / f".partial_posthog_sessions_{stamp}.csv"

    for path in (partial_events_path, partial_sessions_path):
        if path.exists():
            path.unlink()

    write_header_state = {"events": True, "sessions": True}
    event_total = 0
    session_total = 0

    for chunk_start, chunk_end in date_chunks(start_date, end_date, chunk_days):
        print(f"Querying {chunk_start:%Y-%m-%d} -> {chunk_end:%Y-%m-%d}")
        event_total += export_kind(project_id, api_key, "events", chunk_start, chunk_end, limit, partial_events_path, sleep, write_header_state)
        session_total += export_kind(project_id, api_key, "sessions", chunk_start, chunk_end, limit, partial_sessions_path, sleep, write_header_state)

    if not partial_events_path.exists() or not partial_sessions_path.exists():
        raise RuntimeError("The download did not generate both expected temporary files.")

    partial_events_path.replace(events_path)
    partial_sessions_path.replace(sessions_path)
    return events_path, sessions_path, event_total, session_total


def main() -> None:
    args = parse_args()
    legacy_project_id, legacy_api_key = read_legacy_credentials(args.legacy_script)
    project_id = args.project_id or legacy_project_id
    api_key = args.api_key or legacy_api_key

    if not project_id or not api_key:
        raise SystemExit(
            "Missing project-id or api-key. Use POSTHOG_PROJECT_ID/POSTHOG_API_KEY "
            "or --legacy-script path\\posthog.py."
        )

    if args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    elif args.start or args.end:
        raise SystemExit("Use --start and --end together, or omit both to download all available history.")
    else:
        print("Detecting available historical range in PostHog...")
        start_date, end_date = detect_available_range(project_id, api_key)

    if end_date < start_date:
        raise SystemExit("--end cannot be earlier than --start.")

    project_dir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir) if args.output_dir else project_dir / "data" / "posthog_raw" / "full"
    print(f"Range to export: {start_date:%Y-%m-%d} -> {end_date:%Y-%m-%d}")
    print(f"Output folder: {output_dir}")

    events_path, sessions_path, event_total, session_total = export_range(
        project_id=project_id,
        api_key=api_key,
        start_date=start_date,
        end_date=end_date,
        chunk_days=args.chunk_days,
        limit=args.limit,
        output_dir=output_dir,
        sleep=args.sleep,
    )

    print("=" * 60)
    print(f"Events exported: {event_total} -> {events_path}")
    print(f"Sessions exported: {session_total} -> {sessions_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
