import pandas as pd
data_dir = f"{__file__}/.."
# Read the CSV file
df = pd.read_csv(f'{data_dir}/dianping_collection_data.csv')

# Group by store and address, calculate average review count
average_reviews = df.groupby(['store', 'address'])['review_cnt'].mean().reset_index()

# Rename the column to be more descriptive
average_reviews.rename(columns={'review_cnt': 'avg_review_cnt'}, inplace=True)

# Round the average to 2 decimal places
average_reviews['avg_review_cnt'] = average_reviews['avg_review_cnt'].round(2)

# Display the results
print(average_reviews)

# Optionally, save to a new CSV file
average_reviews.to_csv(f'{data_dir}/dianping_average_reviews.csv', index=False)
print("\nResults saved to 'dianping_average_reviews.csv'")
