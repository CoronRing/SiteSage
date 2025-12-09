import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import sys
from pathlib import Path

# =====================
# Load and preprocess
# =====================
df = pd.read_csv(sys.argv[1])

# Parse dates safely
df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
df = df.dropna(subset=["date"])

# Sort by store and date
df = df.sort_values(["store", "date"])

# Pivot: one column per store
pivot_df = (
    df.pivot_table(
        index="date",
        columns="store",
        values="review_cnt",
        aggfunc="sum",
    )
    .sort_index()
)

# =====================
# NeurIPS Plot Style
# =====================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "axes.titlesize": 15,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 11,
    "axes.linewidth": 1.0,
    "figure.dpi": 400,
})

fig, ax = plt.subplots(figsize=(12, 6))

# =====================
# Plot Each Store Line
# =====================
store_colors = {}

for store in pivot_df.columns:
    # Drop NaNs for better-connected lines
    series = pivot_df[store].dropna()

    if len(series) == 0:
        continue

    line, = ax.plot(
        series.index,
        series.values,
        marker="o",
        linewidth=2.0,
        label=store,
    )
    store_colors[store] = line.get_color()

# =====================
# Plot Mean Lines
# =====================
mean_counts = pivot_df.mean()
x_min, x_max = pivot_df.index.min(), pivot_df.index.max()

for store, mean_value in mean_counts.items():
    ax.hlines(
        y=mean_value,
        xmin=x_min,
        xmax=x_max,
        color=store_colors.get(store, "gray"),
        linestyles="--",
        linewidth=1.2,
        alpha=0.9,
    )

# =====================
# Axis Labels / Title
# =====================
ax.set_xlabel("Date")
ax.set_ylabel("Review Count")
ax.set_title("Review Counts Over Time by Store")

# cleaner legend
ax.legend(
    title="Store",
    frameon=False,
    loc="upper left",
    # bbox_to_anchor=(1.01, 1.0)  # place outside plot for neatness
)

# =====================
# Beautify X Axis (Date)
# =====================
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
ax.xaxis.set_major_locator(mdates.AutoDateLocator())

fig.autofmt_xdate(rotation=30)

# =====================
# NeurIPS-style grid & spines
# =====================
ax.grid(axis="y", linestyle="--", linewidth=0.8, color="0.85")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Tight layout
plt.tight_layout()

# Save
output_path = Path("review_trends_by_store.png")
plt.savefig(output_path, bbox_inches="tight")
print("Saved to:", output_path)
plt.close(fig)
