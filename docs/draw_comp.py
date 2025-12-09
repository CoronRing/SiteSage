import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

STORE_LINE_RE = re.compile(r"^-----Store\d+:\s*(.+?)\s*-\s*Scores:\s*(.+)$")
PAIR_RE = re.compile(r"^Pair\s+\d+:\s*(.+?)\s+vs\s+(.+)$")
PAIR_SCORE_RE = re.compile(r"^Final scores\s*->\s*A\s*([0-9.]+)\s*\|\s*B\s*([0-9.]+)$")


@dataclass
class StorePlotData:
    store: str
    final_score: float
    df: pd.DataFrame


def parse_final_scores(markdown_path: Path) -> Dict[str, float]:
    """Extract the latest final score for each store from final_result_recording.md."""
    text = markdown_path.read_text(encoding="utf-8")
    store_scores: Dict[str, float] = {}
    pending_pair: Optional[Tuple[str, str]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        store_match = STORE_LINE_RE.match(line)
        if store_match:
            store_name, score_blob = store_match.groups()
            first_score = score_blob.strip().split()[0]
            try:
                store_scores[store_name.strip()] = float(first_score)
            except ValueError:
                pass
            continue

        pair_match = PAIR_RE.match(line)
        if pair_match:
            pending_pair = (pair_match.group(1).strip(), pair_match.group(2).strip())
            continue

        pair_score_match = PAIR_SCORE_RE.match(line)
        if pair_score_match and pending_pair:
            score_a, score_b = pair_score_match.groups()
            try:
                store_scores[pending_pair[0]] = float(score_a)
                store_scores[pending_pair[1]] = float(score_b)
            except ValueError:
                pass
            pending_pair = None

    return store_scores


def load_review_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["review_cnt"] = pd.to_numeric(df["review_cnt"], errors="coerce")
    df = df.dropna(subset=["review_cnt"])
    return df


def scale_reviews(df: pd.DataFrame) -> pd.DataFrame:
    min_cnt = df["review_cnt"].min()
    max_cnt = df["review_cnt"].max()
    if pd.isna(min_cnt) or pd.isna(max_cnt):
        df["review_scaled"] = pd.NA
        return df

    if max_cnt == min_cnt:
        df["review_scaled"] = 5.0
        return df

    df["review_scaled"] = 10 * (df["review_cnt"] - min_cnt) / (max_cnt - min_cnt)
    return df


def gather_plot_data(
    df: pd.DataFrame,
    final_scores: Dict[str, float],
    stores: Iterable[str],
) -> List[StorePlotData]:
    store_data: List[StorePlotData] = []
    seen = set()

    for store in stores:
        store = store.strip()
        if not store or store in seen:
            continue
        seen.add(store)

        if store not in final_scores:
            print(f"[WARN] Final score not found for store: {store}")
            continue

        store_df = df[df["store"] == store].copy()
        if store_df.empty:
            print(f"[WARN] No review data found for store: {store}")
            continue

        store_df = store_df.sort_values("date")
        store_data.append(
            StorePlotData(
                store=store,
                final_score=final_scores[store],
                df=store_df,
            )
        )

    return store_data


def resolve_store_queries(
    queries: Iterable[str],
    review_df: pd.DataFrame,
    final_scores: Dict[str, float],
) -> List[str]:
    """Expand each query to all matching store names."""
    ordered_stores = list(dict.fromkeys(review_df["store"].dropna()))
    resolved: List[str] = []

    for raw_query in queries:
        query = raw_query.strip()
        if not query:
            continue
        query_lower = query.lower()

        matches = [
            store
            for store in ordered_stores
            if query_lower in store.lower()
        ]

        if not matches:
            print(f"[WARN] No stores matched query: '{query}'")
            continue

        added = False
        for store in matches:
            if store not in final_scores:
                print(f"[WARN] Final score missing for matched store '{store}'")
                continue
            if store in resolved:
                continue
            resolved.append(store)
            added = True

        if not added:
            print(f"[WARN] Query '{query}' matched stores without usable data.")

    return resolved


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "axes.titlesize": 15,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 11,
            "axes.linewidth": 1.0,
            "figure.dpi": 300,
        }
    )


def plot_review_trends(
    stores_data: List[StorePlotData],
    output_path: Path,
) -> Dict[str, str]:
    fig, ax = plt.subplots(figsize=(12, 6))
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    store_colors: Dict[str, str] = {}
    store_handles: List[Line2D] = []

    for idx, store_data in enumerate(stores_data):
        color = color_cycle[idx % len(color_cycle)]
        store_colors[store_data.store] = color
        line, = ax.plot(
            store_data.df["date"],
            store_data.df["review_scaled"],
            marker="o",
            linewidth=2.0,
            label=store_data.store,
            color=color,
        )
        store_handles.append(line)

        avg_val = store_data.df["review_scaled"].mean()
        ax.hlines(
            y=avg_val,
            xmin=store_data.df["date"].min(),
            xmax=store_data.df["date"].max(),
            color=color,
            linestyles="--",
            linewidth=1.2,
            alpha=0.9,
        )

        ax.hlines(
            y=store_data.final_score,
            xmin=store_data.df["date"].min(),
            xmax=store_data.df["date"].max(),
            color=color,
            linestyles="-",
            linewidth=1.0,
            alpha=0.7,
        )

    ax.set_xlabel("Date")
    ax.set_ylabel("Scaled Review Count / Score (0-10)")
    ax.set_title("Ground Truth Review Counts vs Final Scores")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30)
    ax.grid(axis="y", linestyle="--", linewidth=0.8, color="0.85")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend1 = ax.legend(handles=store_handles, title="Stores", loc="upper left")
    ax.add_artist(legend1)

    style_handles = [
        Line2D([0], [0], color="black", linestyle="-", linewidth=2, label="Scaled Reviews", marker="o"),
        Line2D([0], [0], color="black", linestyle="--", linewidth=1.2, label="Avg Review Count"),
        Line2D([0], [0], color="black", linestyle="-", linewidth=1.0, label="Final Score"),
    ]
    ax.legend(handles=style_handles, title="Line Style", loc="upper right")

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[INFO] Saved review trend plot to {output_path}")

    return store_colors


def compute_scaled_totals(stores_data: List[StorePlotData]) -> Dict[str, float]:
    """Sum each store's review counts and scale totals to a 0-10 range."""
    totals: Dict[str, float] = {}
    for store_data in stores_data:
        total = store_data.df["review_cnt"].sum()
        if pd.isna(total):
            continue
        totals[store_data.store] = float(total)

    if not totals:
        return {}

    min_total = min(totals.values())
    max_total = max(totals.values())

    if max_total == min_total:
        return {store: 10.0 for store in totals}

    scaled = {
        store: 10 * (total - min_total) / (max_total - min_total)
        for store, total in totals.items()
    }
    return scaled


def plot_score_vs_average(
    stores_data: List[StorePlotData],
    store_colors: Dict[str, str],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    scaled_totals = compute_scaled_totals(stores_data)

    for store_data in stores_data:
        scaled_total = scaled_totals.get(store_data.store)
        if scaled_total is None:
            print(f"[WARN] Could not compute scaled total for {store_data.store}")
            continue
        ax.scatter(
            scaled_total,
            store_data.final_score,
            s=80,
            label=store_data.store,
            color=store_colors.get(store_data.store, None),
            edgecolor="black",
            linewidth=0.5,
        )

    ax.set_xlabel("Scaled Total Review Count (0-10)")
    ax.set_ylabel("Final Score (0-10)")
    ax.set_title("Final Score vs Scaled Total Review Count")
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(0, 10)
    ax.grid(True, linestyle="--", linewidth=0.8, color="0.85")
    ax.legend(title="Store")

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[INFO] Saved score comparison plot to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Sitesage final scores to Dianping review counts."
    )
    parser.add_argument(
        "stores",
        nargs="+",
        help="Store names or substrings to visualize (substring matches expand automatically).",
    )
    base_path = Path(__file__).resolve()
    parser.add_argument(
        "--results-file",
        type=Path,
        default=base_path.parents[0] / "final_result_recording.md",
        help="Path to final_result_recording.md",
    )
    parser.add_argument(
        "--reviews-file",
        type=Path,
        default=base_path.parents[0] / "dianping_collection_data.csv",
        help="Path to dianping_collection_data.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to store generated plots.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    final_scores = parse_final_scores(args.results_file)
    review_df = load_review_data(args.reviews_file)
    review_df = scale_reviews(review_df)

    resolved_stores = resolve_store_queries(args.stores, review_df, final_scores)
    stores_data = gather_plot_data(review_df, final_scores, resolved_stores)
    if not stores_data:
        print("[ERROR] No stores could be visualized. Check inputs.")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trend_path = args.output_dir / "store_review_trends_{}.png".format(args.stores[0])
    scatter_path = args.output_dir / "store_score_vs_reviews_{}.png".format(args.stores[0])

    store_colors = plot_review_trends(stores_data, trend_path)
    plot_score_vs_average(stores_data, store_colors, scatter_path)


if __name__ == "__main__":
    main()
