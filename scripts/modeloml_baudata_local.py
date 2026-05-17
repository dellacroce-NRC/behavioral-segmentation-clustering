from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
from zoneinfo import ZoneInfo


os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")
TIMEZONE_NAME = "America/Santiago"
DOWNLOAD_ACTIONS = {"ver pdf", "exportar excel"}
pd = None
KMeans = None
StandardScaler = None
TIMEZONE = None


def ensure_dependencies() -> None:
    global pd, KMeans, StandardScaler, TIMEZONE
    try:
        import pandas as pandas_module
        from sklearn.cluster import KMeans as kmeans_class
        from sklearn.preprocessing import StandardScaler as scaler_class
        timezone = ZoneInfo(TIMEZONE_NAME)
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing local dependencies. Run from the project folder:\n"
            "  python -m venv .venv\n"
            "  .\\.venv\\Scripts\\Activate.ps1\n"
            "  pip install -r requirements.txt"
        ) from exc
    except Exception as exc:
        raise SystemExit(
            "Could not load America/Santiago timezone. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    pd = pandas_module
    KMeans = kmeans_class
    StandardScaler = scaler_class
    TIMEZONE = timezone


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Process PostHog CSVs and generate local session clustering.")
    parser.add_argument("--results-dir", default=str(project_dir / "data" / "posthog_raw" / "full"))
    parser.add_argument("--output-dir", default=str(project_dir / "outputs" / "kmeans_k3"))
    parser.add_argument("--events-file", default=None)
    parser.add_argument("--sessions-file", default=None)
    parser.add_argument("--clusters", type=int, default=3)
    parser.add_argument("--download-weight", type=float, default=5.0)
    return parser.parse_args()


def latest_csv(results_dir: Path, pattern: str) -> Path:
    files = sorted(glob.glob(str(results_dir / pattern)))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern} found in {results_dir}")
    return Path(files[-1])


def load_inputs(args: argparse.Namespace):
    results_dir = Path(args.results_dir)
    events_path = Path(args.events_file) if args.events_file else latest_csv(results_dir, "posthog_events_*.csv")
    sessions_path = Path(args.sessions_file) if args.sessions_file else latest_csv(results_dir, "posthog_sessions_*.csv")

    df_events = pd.read_csv(events_path)
    df_sessions = pd.read_csv(sessions_path)
    return df_events, df_sessions, events_path, sessions_path


def prepare_dates(df_events, df_sessions):
    df_events = df_events.copy()
    df_sessions = df_sessions.copy()

    df_events["event_ts"] = pd.to_datetime(df_events["timestamp"], errors="coerce", utc=True)
    df_sessions["session_start"] = pd.to_datetime(df_sessions["$start_timestamp"], errors="coerce", utc=True)
    df_sessions["duration"] = pd.to_numeric(df_sessions["duration"], errors="coerce").fillna(0)
    df_sessions["session_end"] = df_sessions["session_start"] + pd.to_timedelta(df_sessions["duration"], unit="s")

    df_events = df_events.dropna(subset=["distinct_id", "event_ts"])
    df_sessions = df_sessions.dropna(subset=["distinct_id", "session_start", "session_end"])
    return df_events, df_sessions


def assign_events_to_sessions(df_events, df_sessions):
    merged = pd.merge(
        df_events,
        df_sessions[["distinct_id", "session_start", "session_end", "duration"]],
        on="distinct_id",
        how="left",
    )
    return merged[
        (merged["event_ts"] >= merged["session_start"])
        & (merged["event_ts"] <= merged["session_end"])
    ].copy()


def build_features(df_merged_filtered):
    if df_merged_filtered.empty:
        raise RuntimeError("No events remained associated to sessions. Check PostHog dates and columns.")

    action = df_merged_filtered["action"].fillna("").astype(str).str.lower()
    df_merged_filtered["is_download"] = (
        (df_merged_filtered["event"] == "download")
        | ((df_merged_filtered["event"] == "action_button") & action.isin(DOWNLOAD_ACTIONS))
    )

    df_features = df_merged_filtered.groupby(["distinct_id", "session_start"], as_index=False).agg(
        marker_select_count=("event", lambda values: (values == "marker_select").sum()),
        search_filter_select_count=("event", lambda values: ((values == "search") | (values == "filter_select")).sum()),
        page_view_count=("event", lambda values: (values == "page_view").sum()),
        download_flag=("is_download", "any"),
        real_duration=("event_ts", lambda values: (values.max() - values.min()).total_seconds() if not values.empty else 0),
    )

    df_features["download_flag"] = df_features["download_flag"].astype(int)
    df_features["start"] = df_features["session_start"].dt.tz_convert(TIMEZONE).dt.tz_localize(None)
    return df_features.drop(columns=["session_start"])


def cluster_features(df_features, clusters: int, download_weight: float):
    df_features = df_features.copy()
    df_features["weighted_download"] = df_features["download_flag"] * download_weight
    features = [
        "marker_select_count",
        "search_filter_select_count",
        "page_view_count",
        "weighted_download",
        "real_duration",
    ]

    scaler = StandardScaler()
    scaled = scaler.fit_transform(df_features[features].fillna(0))

    kmeans = KMeans(n_clusters=clusters, random_state=42, n_init="auto")
    df_features["cluster"] = kmeans.fit_predict(scaled)
    return df_features


def export_outputs(df_features, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "resultados_clustering_posthog.csv"
    xlsx_path = output_dir / "resultados_clustering_posthog.xlsx"

    df_features.to_csv(csv_path, index=False, encoding="utf-8")
    try:
        df_features.to_excel(xlsx_path, index=False)
    except Exception as exc:
        print(f"Excel export failed ({exc}). CSV output is still available.")
        xlsx_path = None

    return csv_path, xlsx_path


def print_summary(df_features, events_path: Path, sessions_path: Path) -> None:
    print("=" * 60)
    print("Processed files")
    print(f"Events:  {events_path}")
    print(f"Sessions: {sessions_path}")
    print("=" * 60)
    print(f"Modeled active sessions: {len(df_features)}")
    print(f"Unique users: {df_features['distinct_id'].nunique()}")
    print(f"Sessions with download/PDF/Excel: {df_features['download_flag'].sum()}")
    print("Processed range:")
    print(f"  From: {df_features['start'].min()}")
    print(f"  To:   {df_features['start'].max()}")
    print("\nCluster averages:")
    cols = ["marker_select_count", "search_filter_select_count", "page_view_count", "download_flag", "real_duration"]
    print(df_features.groupby("cluster")[cols].mean().round(2))
    print("\nCluster distribution:")
    print((df_features["cluster"].value_counts(normalize=True).sort_index() * 100).round(2))


def main() -> None:
    args = parse_args()
    ensure_dependencies()
    df_events, df_sessions, events_path, sessions_path = load_inputs(args)
    print(f"Loaded files: {len(df_events)} events and {len(df_sessions)} sessions.")

    df_events, df_sessions = prepare_dates(df_events, df_sessions)
    df_merged_filtered = assign_events_to_sessions(df_events, df_sessions)
    print(f"Events linked to sessions: {len(df_merged_filtered)}")

    df_features = build_features(df_merged_filtered)
    df_features = cluster_features(df_features, args.clusters, args.download_weight)
    csv_path, xlsx_path = export_outputs(df_features, Path(args.output_dir))

    print_summary(df_features, events_path, sessions_path)
    print("=" * 60)
    print(f"CSV generated: {csv_path}")
    if xlsx_path:
        print(f"Excel generated: {xlsx_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
