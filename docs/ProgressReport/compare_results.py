import csv
import itertools
from pathlib import Path


def load_results(csv_path: Path):
    """Load result rows into a list of dicts with typed values."""
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                {
                    "store": row["store"],
                    "gt_rank": float(row["gt_rank"]),
                    "pred_score": float(row["pred_score"]),
                }
            )
    return rows


def evaluate_pairwise_accuracy(rows):
    """Compare every pair of stores and count ordering hits."""
    total = 0
    hits = 0
    margin = 0

    for first, second in itertools.combinations(rows, 2):
        gt_diff = second["gt_rank"] - first["gt_rank"]
        score_diff = first["pred_score"] - second["pred_score"]

        if (gt_diff > 0 and score_diff > 0) or (gt_diff < 0 and score_diff < 0):
            print(first, second)
            margin += abs(score_diff)
            hits += 1
        total += 1

    accuracy = hits / total if total else 0.0
    margin = margin / hits
    return hits, total, accuracy, margin


def main():
    csv_path = Path("result-nov16.csv")
    rows = load_results(csv_path)

    if len(rows) < 2:
        print("Need at least two stores to compare.")
        return

    hits, total, accuracy, margin = evaluate_pairwise_accuracy(rows)
    print(f"hits: {hits}")
    print(f"total comparisons: {total}")
    print(f"accuracy: {accuracy:.4f}")
    print(f"average margin: {margin:.4f}")


if __name__ == "__main__":
    main()
