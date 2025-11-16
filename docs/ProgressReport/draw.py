import matplotlib.pyplot as plt

import pandas as pd
import sys

df = pd.read_csv(sys.argv[1])

# Load the data, parse the dates, and sort for nicer plotting.
df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
df = df.sort_values(["store", "date"])

# Pivot the table so that each store becomes a column.
pivot_df = (
    df.pivot_table(
        index="date",
        columns="store",
        values="review_cnt",
        aggfunc="sum",
    )
    .sort_index()
)

fig, ax = plt.subplots(figsize=(10, 6))

store_colors = {}

# Draw one line per store and remember its color so mean lines match.
for store in pivot_df.columns:
    line, = ax.plot(pivot_df.index, pivot_df[store], marker="o", label=store)
    store_colors[store] = line.get_color()

mean_counts = pivot_df.mean()
x_min, x_max = pivot_df.index.min(), pivot_df.index.max()

for store, mean_value in mean_counts.items():
    ax.hlines(
        mean_value,
        x_min,
        x_max,
        colors=store_colors.get(store, None),
        linestyles="--",
        linewidth=1,
    )

ax.set_xlabel("Date")
ax.set_ylabel("Review Count")
ax.set_title("Review Counts Over Time by Store")
ax.legend(title="Store", loc="best")
ax.grid(True, linestyle="--", linewidth=0.5)

fig.autofmt_xdate()
plt.tight_layout()
plt.savefig("data.jpg")
