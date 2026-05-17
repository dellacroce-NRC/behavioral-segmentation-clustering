from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

import modeloml_baudata_local as base_model


FEATURE_COLUMNS = [
    "marker_select_count",
    "search_filter_select_count",
    "page_view_count",
    "weighted_download",
    "real_duration",
]


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Compare clustering alternatives for the BauData project.")
    parser.add_argument("--results-dir", default=str(project_dir / "data" / "posthog_raw" / "full"))
    parser.add_argument("--output-dir", default=str(project_dir / "outputs" / "model_comparison"))
    parser.add_argument("--events-file", default=None)
    parser.add_argument("--sessions-file", default=None)
    parser.add_argument("--min-clusters", type=int, default=2)
    parser.add_argument("--max-clusters", type=int, default=6)
    parser.add_argument("--download-weight", type=float, default=5.0)
    return parser.parse_args()


def build_feature_table(args: argparse.Namespace):
    base_model.ensure_dependencies()
    load_args = argparse.Namespace(results_dir=args.results_dir, events_file=args.events_file, sessions_file=args.sessions_file)
    df_events, df_sessions, events_path, sessions_path = base_model.load_inputs(load_args)
    df_events, df_sessions = base_model.prepare_dates(df_events, df_sessions)
    df_merged = base_model.assign_events_to_sessions(df_events, df_sessions)
    df_features = base_model.build_features(df_merged)
    df_features["weighted_download"] = df_features["download_flag"] * args.download_weight
    return df_features, events_path, sessions_path


def scaled_matrix(df_features: pd.DataFrame) -> np.ndarray:
    scaler = StandardScaler()
    return scaler.fit_transform(df_features[FEATURE_COLUMNS].fillna(0))


def summarize_labels(labels: np.ndarray, scaled: np.ndarray) -> dict[str, float | int]:
    total = len(labels)
    unique_labels = sorted(set(labels))
    non_noise = [label for label in unique_labels if label != -1]
    n_clusters = len(non_noise)
    noise_pct = float((labels == -1).mean() * 100) if -1 in unique_labels else 0.0

    counts = pd.Series(labels).value_counts(normalize=True) * 100
    largest_cluster_pct = float(counts.max())
    smallest_cluster_pct = float(counts.min())
    balance_gap_pct = largest_cluster_pct - smallest_cluster_pct

    valid_for_metrics = len(set(labels)) >= 2 and len(set(labels)) < total
    if valid_for_metrics:
        silhouette = float(silhouette_score(scaled, labels))
        calinski = float(calinski_harabasz_score(scaled, labels))
        davies = float(davies_bouldin_score(scaled, labels))
    else:
        silhouette = math.nan
        calinski = math.nan
        davies = math.nan

    return {
        "n_clusters": n_clusters,
        "noise_pct": round(noise_pct, 2),
        "largest_cluster_pct": round(largest_cluster_pct, 2),
        "smallest_cluster_pct": round(smallest_cluster_pct, 2),
        "balance_gap_pct": round(balance_gap_pct, 2),
        "silhouette": round(silhouette, 4) if not math.isnan(silhouette) else math.nan,
        "calinski_harabasz": round(calinski, 2) if not math.isnan(calinski) else math.nan,
        "davies_bouldin": round(davies, 4) if not math.isnan(davies) else math.nan,
    }


def evaluate_candidates(scaled: np.ndarray, min_clusters: int, max_clusters: int):
    rows: list[dict[str, object]] = []
    labels_by_candidate: dict[str, np.ndarray] = {}

    for k in range(min_clusters, max_clusters + 1):
        candidate = f"kmeans_k{k}"
        labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(scaled)
        labels_by_candidate[candidate] = labels
        rows.append({"candidate": candidate, "model": "KMeans", "parameter": f"k={k}", **summarize_labels(labels, scaled)})

    for k in range(min_clusters, max_clusters + 1):
        candidate = f"gmm_k{k}"
        labels = GaussianMixture(n_components=k, random_state=42, n_init=5).fit_predict(scaled)
        labels_by_candidate[candidate] = labels
        rows.append({"candidate": candidate, "model": "GaussianMixture", "parameter": f"k={k}", **summarize_labels(labels, scaled)})

    for k in range(min_clusters, max_clusters + 1):
        candidate = f"agglomerative_k{k}"
        labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(scaled)
        labels_by_candidate[candidate] = labels
        rows.append({"candidate": candidate, "model": "Agglomerative", "parameter": f"k={k}", **summarize_labels(labels, scaled)})

    for eps in [0.35, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
        for min_samples in [5, 10, 20]:
            candidate = f"dbscan_eps{eps}_min{min_samples}".replace(".", "p")
            labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled)
            labels_by_candidate[candidate] = labels
            rows.append({"candidate": candidate, "model": "DBSCAN", "parameter": f"eps={eps}, min_samples={min_samples}", **summarize_labels(labels, scaled)})

    return pd.DataFrame(rows), labels_by_candidate


def rank_candidates(df_results: pd.DataFrame) -> pd.DataFrame:
    df = df_results.copy()
    valid = (
        df["silhouette"].notna()
        & df["davies_bouldin"].notna()
        & (df["n_clusters"] >= 2)
        & (df["noise_pct"] <= 30)
        & (df["largest_cluster_pct"] <= 90)
    )
    df["valid_candidate"] = valid
    df["rank_silhouette"] = df["silhouette"].rank(ascending=False, method="min")
    df["rank_davies"] = df["davies_bouldin"].rank(ascending=True, method="min")
    df["rank_calinski"] = df["calinski_harabasz"].rank(ascending=False, method="min")
    df["rank_balance"] = df["balance_gap_pct"].rank(ascending=True, method="min")
    df["selection_score"] = (
        df["rank_silhouette"]
        + df["rank_davies"]
        + df["rank_calinski"]
        + (0.5 * df["rank_balance"])
        + (df["noise_pct"] / 10)
    )
    df.loc[~df["valid_candidate"], "selection_score"] = np.inf
    return df.sort_values(["selection_score", "silhouette"], ascending=[True, False])


def df_to_markdown(df: pd.DataFrame) -> str:
    printable = df.copy().astype(str)
    header = "| " + " | ".join(printable.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(printable.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in printable.to_numpy()]
    return "\n".join([header, separator, *rows])


def write_report(output_dir: Path, ranked: pd.DataFrame, best_candidate: str, events_path: Path, sessions_path: Path) -> Path:
    report_path = output_dir / "reporte_comparacion_modelos.md"
    top = ranked.head(10)
    best = ranked.loc[ranked["candidate"] == best_candidate].iloc[0]
    text = f"""# Clustering Model Comparison - BauData

## Files used

- Events: `{events_path}`
- Sessions: `{sessions_path}`

## Recommendation

Recommended candidate: `{best_candidate}` ({best['model']}, {best['parameter']}).

The recommendation combines internal clustering metrics and business interpretability:

- Silhouette: higher means better separation.
- Davies-Bouldin: lower means less overlap.
- Calinski-Harabasz: higher means better relative separation.
- Balance: avoids solutions where almost all sessions fall into one cluster.
- Noise: penalizes models that leave too many cases unclassified.

## Top 10 candidates

{df_to_markdown(top[['candidate', 'model', 'parameter', 'n_clusters', 'noise_pct', 'largest_cluster_pct', 'silhouette', 'calinski_harabasz', 'davies_bouldin', 'selection_score']])}

## Executive reading

K-Means is useful when it provides compact, stable, and explainable behavioral groups. DBSCAN can help detect outliers, but it is often less practical for commercial teams if it creates too much noise. Gaussian Mixture can capture more flexible shapes, but its business interpretation must remain clear before replacing K-Means.
"""
    report_path.write_text(text, encoding="utf-8")
    return report_path


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_features, events_path, sessions_path = build_feature_table(args)
    scaled = scaled_matrix(df_features)
    raw_results, labels_by_candidate = evaluate_candidates(scaled, args.min_clusters, args.max_clusters)
    ranked = rank_candidates(raw_results)

    best_candidate = str(ranked.iloc[0]["candidate"])
    best_labels = labels_by_candidate[best_candidate]
    assignments = df_features.copy()
    assignments["modelo_recomendado"] = best_candidate
    assignments["cluster_recomendado"] = best_labels

    ranked.to_csv(output_dir / "comparacion_modelos_clustering.csv", index=False, encoding="utf-8")
    assignments.to_csv(output_dir / "asignacion_modelo_recomendado.csv", index=False, encoding="utf-8")
    df_features.to_csv(output_dir / "features_base_clustering.csv", index=False, encoding="utf-8")
    report_path = write_report(output_dir, ranked, best_candidate, events_path, sessions_path)

    print("=" * 70)
    print("Model comparison finished")
    print(f"Sessions evaluated: {len(df_features)}")
    print(f"Unique users: {df_features['distinct_id'].nunique()}")
    print(f"Recommended model: {best_candidate}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
