# Import pandas to load, clean, and analyze tabular data
import pandas as pd


# ==================================================
# 1. LOAD AND INSPECT ORDERS DATA
# ==================================================

# Load the orders CSV file into a DataFrame
orders = pd.read_csv("olist_orders_dataset.csv")

# Check the number of rows and columns
print(orders.shape)

# Display all column names
print(orders.columns)

# Display the first five rows
print(orders.head())

# Count missing values in every column
print(orders.isnull().sum())

# Count orders by status, such as delivered or canceled
print(orders["order_status"].value_counts())


# ==================================================
# 2. CHECK MISSING DELIVERY DATES
# ==================================================

# Find delivered orders whose actual delivery date is missing
delivered_missing_date = orders[
    (orders["order_status"] == "delivered") &
    (orders["order_delivered_customer_date"].isnull())
]

# Display the matching orders
print(delivered_missing_date)

# Count delivered orders with missing delivery dates
print("Delivered orders with missing delivery date:",
      len(delivered_missing_date))

# Compare missing and available delivery dates across order statuses
print(
    pd.crosstab(
        orders["order_status"],
        orders["order_delivered_customer_date"].isnull()
    )
)


# ==================================================
# 3. CONVERT DATE COLUMNS
# ==================================================

# Check the original data types of all columns
print(orders.dtypes)

# List the columns that contain dates and timestamps
date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date"
]

# Convert date columns from text into datetime format
for column in date_columns:
    orders[column] = pd.to_datetime(orders[column])

# Verify that the date columns were converted successfully
print(orders.dtypes)


# ==================================================
# 4. CALCULATE DELIVERY DELAY
# ==================================================

# Calculate the difference between actual and estimated delivery dates
# Positive values mean late delivery; negative values mean early delivery
orders["delivery_delay_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_estimated_delivery_date"]
).dt.days

# Display delivery dates and calculated delays for the first 10 orders
print(orders[[
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "delivery_delay_days"
]].head(10))

# Summarize delivery delays using count, mean, median, minimum, and maximum
print(orders["delivery_delay_days"].describe())

# Find orders delivered more than 30 days after the estimated date
late_orders = orders[orders["delivery_delay_days"] > 30]

# Check how many extremely late orders were found
print(late_orders.shape)

# Display details of the first 10 extremely late orders
print(late_orders[
    [
        "order_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "delivery_delay_days"
    ]
].head(10))


# ==================================================
# 5. LOAD AND INSPECT ORDER ITEMS
# ==================================================

# Load the order items dataset
items = pd.read_csv("olist_order_items_dataset.csv")

# Check the dataset size, column names, and first five rows
print(items.shape)
print(items.columns)
print(items.head())

# Find orders with the highest number of item rows
# This helps us understand that one order can contain multiple items
print(items["order_id"].value_counts().head(10))


# ==================================================
# 6. CALCULATE ORDER VALUE
# ==================================================

# Add product price and freight cost for each item row
items["total_item_value"] = items["price"] + items["freight_value"]

# Group item rows by order and calculate total value per order
order_value = (
    items.groupby("order_id")["total_item_value"]
    .sum()
    .reset_index()
)

# Display the first 10 calculated order values
print(order_value.head(10))

# Check the number of unique orders in the aggregated table
print(order_value["order_id"].nunique())

# Check the number of rows; it should equal the number of unique order IDs
print(len(order_value))


# ==================================================
# 7. MERGE ORDER VALUES INTO ORDERS
# ==================================================

# Add total item value to the orders dataset using order_id
# Left join keeps every row from the original orders dataset
orders = orders.merge(
    order_value,
    on="order_id",
    how="left"
)

# Check whether the merge preserved the original number of order rows
print(orders.shape)

# Display order status, delay, and value together
print(orders[[
    "order_id",
    "order_status",
    "delivery_delay_days",
    "total_item_value"
]].head(10))

# Check the dataset shape again
print(orders.shape)

# Display the same sample again for verification
print(orders[[
    "order_id",
    "order_status",
    "delivery_delay_days",
    "total_item_value"
]].head(10))


# ==================================================
# 8. CLASSIFY DELIVERY PERFORMANCE
# ==================================================

# Classify orders as Early, On Time, or Late based on delay days
# Early: delivered more than 1 day before the estimate
# On Time: delivered 1 day early or exactly on the estimated date
# Late: delivered after the estimated date
orders["delivery_performance"] = pd.cut(
    orders["delivery_delay_days"],
    bins=[-float("inf"), -1, 0, float("inf")],
    labels=["Early", "On Time", "Late"]
)

# Count orders in each delivery category, including missing values
print(orders["delivery_performance"].value_counts(dropna=False))

# Calculate the average total item value for each delivery category
print(
    orders.groupby("delivery_performance")["total_item_value"].mean()
)

# Calculate what percentage of all orders falls into each category
# Missing delivery classifications are included in the percentages
print(
    orders["delivery_performance"]
    .value_counts(normalize=True, dropna=False)
    .mul(100)
)


# ==================================================
# 9. LOAD AND INSPECT PRODUCTS
# ==================================================

# Load the product details dataset
products = pd.read_csv("olist_products_dataset.csv")

# Inspect the product dataset
print(products.shape)
print(products.columns)
print(products.head())


# ==================================================
# 10. CONNECT ITEMS WITH PRODUCT CATEGORIES
# ==================================================

# Load the order items dataset for category-level analysis
order_items = pd.read_csv("olist_order_items_dataset.csv")

# Inspect the order items data
print(order_items.shape)
print(order_items.columns)
print(order_items.head())

# Add product category names to each order item using product_id
order_items_products = order_items.merge(
    products[["product_id", "product_category_name"]],
    on="product_id",
    how="left"
)

# Check the merged dataset size and sample rows
print(order_items_products.shape)
print(order_items_products.head())


# ==================================================
# 11. CALCULATE SALES BY PRODUCT CATEGORY
# ==================================================

# Calculate total product price for each category
# Freight charges are not included in this category sales metric
category_sales = (
    order_items_products
    .groupby("product_category_name")["price"]
    .sum()
    .sort_values(ascending=False)
)

# Display the 10 categories with the highest total sales
print(category_sales.head(10))


# ==================================================
# 12. COUNT ORDERS BY PRODUCT CATEGORY
# ==================================================

# Count unique orders containing each category
# An order containing the same category in multiple items is counted once
category_orders = (
    order_items_products
    .groupby("product_category_name")["order_id"]
    .nunique()
    .sort_values(ascending=False)
)

# Display the 10 categories with the most unique orders
print(category_orders.head(10))


# ==================================================
# 13. CALCULATE AVERAGE SALES PER CATEGORY ORDER
# ==================================================

# Divide category sales by the number of unique orders containing that category
# This is not the average value of the entire shopping basket
category_average_order = (
    order_items_products
    .groupby("product_category_name")
    .apply(
        lambda group: group["price"].sum()
        / group["order_id"].nunique(),
        include_groups=False
    )
    .sort_values(ascending=False)
)

# Display the categories with the highest sales per unique category order
print(category_average_order.head(10))


# ==================================================
# 14. CALCULATE CATEGORY SALES CONTRIBUTION
# ==================================================

# Calculate each category's percentage of total product sales
category_sales_percentage = (
    category_sales / category_sales.sum() * 100
).round(2)

# Display the top 10 categories by sales contribution
print(category_sales_percentage.head(10))


# ==================================================
# 15. ANALYZE MONTHLY SALES
# ==================================================

# Attach order purchase timestamps to the order items
monthly_sales = (
    order_items_products
    .merge(
        orders[["order_id", "order_purchase_timestamp"]],
        on="order_id",
        how="left"
    )
)

# Extract the month from each order's purchase timestamp
monthly_sales["month"] = (
    monthly_sales["order_purchase_timestamp"]
    .dt.to_period("M")
)

# Calculate total product sales for each month
monthly_sales = (
    monthly_sales
    .groupby("month")["price"]
    .sum()
)

# Display monthly sales totals
print(monthly_sales)


# ==================================================
# 16. VISUALIZE MONTHLY SALES
# ==================================================

# Import matplotlib for creating charts
import matplotlib.pyplot as plt

# Plot monthly sales as a line chart
monthly_sales.plot(
    kind="line",
    marker="o",
    figsize=(12, 5)
)

# Add a title and axis labels
plt.title("Monthly Sales Trend")
plt.xlabel("Month")
plt.ylabel("Total Product Sales (R$)")

# Rotate month labels so they are easier to read
plt.xticks(rotation=45)

# Display grid lines and adjust spacing
plt.grid(True)
plt.tight_layout()

# Display the chart
plt.show()


# ==================================================
# 17. CALCULATE MONTHLY SALES GROWTH
# ==================================================

# Calculate percentage change compared with the previous available month
monthly_growth = monthly_sales.pct_change() * 100

# Display monthly sales growth percentages
print("Monthly Sales Growth (%):")
print(monthly_growth.round(2))


# ==================================================
# 18. FIND HIGHEST AND LOWEST SALES MONTHS
# ==================================================

# Find the month with the highest recorded sales
print("Highest Sales Month:", monthly_sales.idxmax())
print("Highest Sales:", monthly_sales.max())

# Find the month with the lowest recorded sales
print("Lowest Sales Month:", monthly_sales.idxmin())
print("Lowest Sales:", monthly_sales.min())


# ==================================================
# 19. DISPLAY CATEGORY SALES CONTRIBUTION
# ==================================================

# Calculate category sales contribution as a percentage
category_sales_share = (
    category_sales / category_sales.sum() * 100
).round(2)

# Display the top 10 categories by sales contribution
print("Top 10 Categories by Sales Contribution (%):")
print(category_sales_share.head(10))


# ==================================================
# 20. VISUALIZE TOP 10 PRODUCT CATEGORIES
# ==================================================

# Import matplotlib for category sales visualization
import matplotlib.pyplot as plt

# Plot the top 10 categories as a horizontal bar chart
category_sales.head(10).sort_values().plot(
    kind="barh",
    title="Top 10 Product Categories by Sales"
)

# Add labels to the chart axes
plt.xlabel("Total Sales (R$)")
plt.ylabel("Product Category")

# Adjust chart spacing and display it
plt.tight_layout()
plt.show()


# ==================================================
# 21. LOAD AND INSPECT CUSTOMER REVIEWS
# ==================================================

# Load the customer reviews dataset
reviews = pd.read_csv("olist_order_reviews_dataset.csv")

# Check the number of rows and columns
print(reviews.shape)

# Display all available review columns
print(reviews.columns)

# Count reviews for each score from 1 to 5
print(reviews["review_score"].value_counts().sort_index())


# ==================================================
# 22. CALCULATE LOW REVIEW PERCENTAGE
# ==================================================

# Identify low reviews, defined here as 1-star or 2-star reviews
low_reviews = reviews[reviews["review_score"] <= 2]

# Calculate the percentage of reviews that are 1 or 2 stars
low_review_percentage = (
    len(low_reviews) / len(reviews)
) * 100

# Display the low review percentage rounded to two decimal places
print("Low Review Percentage:", round(low_review_percentage, 2))

# ==================================================
# 23. ANALYZE DELIVERY PERFORMANCE VS CUSTOMER REVIEWS
# ==================================================

# Connect customer reviews with delivery performance using order_id
review_delivery = reviews.merge(
    orders[["order_id", "delivery_performance"]],
    on="order_id",
    how="inner"
)

# Calculate the average review score for each delivery category
average_review_by_delivery = (
    review_delivery
    .groupby("delivery_performance", observed=True)["review_score"]
    .mean()
    .round(2)
)

# Display the average customer rating for each delivery category
print("Average Review Score by Delivery Performance:")
print(average_review_by_delivery)

# ==================================================
# 24. CUSTOMER EXPERIENCE RISK BY PRODUCT CATEGORY
# ==================================================

# Connect product category information with order delivery performance
category_delivery = order_items_products.merge(
    orders[["order_id", "delivery_performance"]],
    on="order_id",
    how="left"
)

# Connect customer review scores using order_id
category_delivery = category_delivery.merge(
    reviews[["order_id", "review_score"]],
    on="order_id",
    how="left"
)

# Group the data by product category
# Calculate sales, unique orders, late delivery percentage, and average rating
category_risk = (
    category_delivery
    .groupby("product_category_name")
    .agg(
        total_sales=("price", "sum"),
        unique_orders=("order_id", "nunique"),
        late_delivery_percentage=(
            "delivery_performance",
            lambda x: (x == "Late").mean() * 100
        ),
        average_review_score=("review_score", "mean")
    )
)

# Round the percentages and ratings for easier reading
category_risk["late_delivery_percentage"] = (
    category_risk["late_delivery_percentage"].round(2)
)

category_risk["average_review_score"] = (
    category_risk["average_review_score"].round(2)
)

# Sort categories by late delivery percentage, from highest to lowest
category_risk = category_risk.sort_values(
    "late_delivery_percentage",
    ascending=False
)

# Display the 10 categories with the highest late delivery percentage
print("Top 10 Categories by Late Delivery Percentage:")
print(category_risk.head(10))


# ==================================================
# 25. TRANSLATE PRODUCT CATEGORIES INTO ENGLISH
# ==================================================

# Load the official category translation lookup table
category_translation = pd.read_csv(
    "product_category_name_translation.csv"
)

# Add English category names to the products dataset
products_english = products.merge(
    category_translation,
    on="product_category_name",
    how="left"
)

# Connect order items with the English product category names
order_items_products_english = order_items.merge(
    products_english[
        ["product_id", "product_category_name_english"]
    ],
    on="product_id",
    how="left"
)

# Display the original and translated category names
print("Product Categories in English:")

print(
    order_items_products_english[
        ["product_id", "product_category_name_english"]
    ].head(10)
)

# Count categories that do not have an English translation
missing_translations = (
    order_items_products_english[
        "product_category_name_english"
    ].isnull().sum()
)

print("Items with missing English translations:", missing_translations)

# ==================================================
# 26. INVESTIGATE MISSING CATEGORY TRANSLATIONS
# ==================================================

# Count rows where the original product category is missing
print(
    "Missing original categories:",
    order_items_products["product_category_name"].isnull().sum()
)

# Display categories that have no English translation
print(
    order_items_products_english.loc[
        order_items_products_english["product_category_name_english"].isnull(),
        ["product_id"]
    ].head(10)
)

# Count unique products with missing English category names
print(
    "Unique products with missing English categories:",
    order_items_products_english.loc[
        order_items_products_english["product_category_name_english"].isnull(),
        "product_id"
    ].nunique()
)

# ==================================================
# 27. HANDLE MISSING ENGLISH CATEGORY NAMES
# ==================================================

# Create a copy so the original merged dataset remains unchanged
category_data = order_items_products_english.copy()

# Replace missing English category names with a clear label
category_data["product_category_name_english"] = (
    category_data["product_category_name_english"]
    .fillna("Unknown Category")
)

# Count item rows in each English category
print("Top 10 Categories in English:")

print(
    category_data
    .groupby("product_category_name_english")["price"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

# Check whether any English category names are still missing
print(
    "Missing English categories:",
    category_data["product_category_name_english"].isnull().sum()
)

# ==================================================
# 28. FINAL CATEGORY REVENUE AND CUSTOMER RISK ANALYSIS
# ==================================================

# Add delivery performance to the English category dataset
category_risk_english = category_data.merge(
    orders[["order_id", "delivery_performance"]],
    on="order_id",
    how="left"
)

# Add customer review scores using order_id
category_risk_english = category_risk_english.merge(
    reviews[["order_id", "review_score"]],
    on="order_id",
    how="left"
)

# Summarize sales, unique orders, delivery performance, and ratings
category_summary = (
    category_risk_english
    .groupby("product_category_name_english")
    .agg(
        total_sales=("price", "sum"),
        unique_orders=("order_id", "nunique"),
        average_review_score=("review_score", "mean"),
        late_delivery_percentage=(
            "delivery_performance",
            lambda x: (x == "Late").mean() * 100
        )
    )
)

# Round the results for readability
category_summary["average_review_score"] = (
    category_summary["average_review_score"].round(2)
)

category_summary["late_delivery_percentage"] = (
    category_summary["late_delivery_percentage"].round(2)
)

# Display categories with the highest total sales
print("Top 10 Categories by Revenue:")
print(
    category_summary
    .sort_values("total_sales", ascending=False)
    .head(10)
)

# ==================================================
# 29. CALCULATE LATE DELIVERY RATE USING UNIQUE ORDERS
# ==================================================

# Keep one row per order for delivery analysis
order_delivery_unique = (
    orders[
        ["order_id", "delivery_performance"]
    ]
    .drop_duplicates(subset="order_id")
    .copy()
)

# Mark whether each order was delivered late
order_delivery_unique["is_late"] = (
    order_delivery_unique["delivery_performance"] == "Late"
)

# Calculate the overall late-delivery rate among orders
# with a known delivery classification
known_delivery = order_delivery_unique.dropna(
    subset=["delivery_performance"]
)

# Display the unique-order late-delivery percentage
print(
    "Late Delivery Rate (Unique Orders):",
    round(known_delivery["is_late"].mean() * 100, 2),
    "%"
)

# Count the orders included in this calculation
print("Orders with Known Delivery Performance:", len(known_delivery))

# ==================================================
# 30. CATEGORY RISK USING UNIQUE ORDERS
# ==================================================

# Start with order ID, product category, and product price
category_order_data = category_data[
    [
        "order_id",
        "product_category_name_english",
        "price"
    ]
].copy()

# Add delivery performance to each order
category_order_data = category_order_data.merge(
    orders[["order_id", "delivery_performance"]],
    on="order_id",
    how="left"
)

# Add customer review scores to each order
category_order_data = category_order_data.merge(
    reviews[["order_id", "review_score"]],
    on="order_id",
    how="left"
)

# Keep one row per order within each product category
# This prevents orders with multiple items in the same category
# from being counted more than once
unique_category_orders = category_order_data.drop_duplicates(
    subset=["order_id", "product_category_name_english"]
).copy()

# Calculate category-level sales and customer experience metrics
category_risk_unique = (
    unique_category_orders
    .groupby("product_category_name_english")
    .agg(
        unique_orders=("order_id", "nunique"),
        average_review_score=("review_score", "mean"),
        late_delivery_percentage=(
            "delivery_performance",
            lambda x: (x == "Late").mean() * 100
        )
    )
)

# Round ratings and percentages for easier reading
category_risk_unique["average_review_score"] = (
    category_risk_unique["average_review_score"].round(2)
)

category_risk_unique["late_delivery_percentage"] = (
    category_risk_unique["late_delivery_percentage"].round(2)
)

# Display the 10 categories with the highest late-delivery percentage
print("Category Risk Based on Unique Orders:")

print(
    category_risk_unique
    .sort_values("late_delivery_percentage", ascending=False)
    .head(10)
)

# ==================================================
# 31. LOAD SELLER DATA
# ==================================================

# Load the seller dataset
sellers = pd.read_csv("olist_sellers_dataset.csv")

# Check the number of sellers and columns
print("Seller Dataset Shape:", sellers.shape)
print("Seller Dataset Columns:")
print(sellers.columns)

# Display the first 5 sellers
print("First 5 Sellers:")
print(sellers.head())

# ==================================================
# 32. STANDARDIZE SELLER LOCATION NAMES
# ==================================================

# Convert city names to consistent capitalization
sellers["seller_city_clean"] = (
    sellers["seller_city"]
    .str.strip()
    .str.title()
)

# Display original and standardized city names
print("Seller City Name Standardization:")

print(
    sellers[
        ["seller_city", "seller_city_clean", "seller_state"]
    ].head(10)
)

# Count unique seller cities before and after standardization
print(
    "Unique cities before:",
    sellers["seller_city"].nunique()
)

print(
    "Unique cities after:",
    sellers["seller_city_clean"].nunique()
)

# ==================================================
# 33. SELLER-WISE REVENUE ANALYSIS
# ==================================================

# Load order items if not already available
# Each row represents a product item sold by a seller

# Calculate revenue and unique orders for each seller
seller_revenue = (
    order_items
    .groupby("seller_id")
    .agg(
        total_sales=("price", "sum"),
        unique_orders=("order_id", "nunique")
    )
    .reset_index()
)

# Sort sellers from highest to lowest sales
seller_revenue = seller_revenue.sort_values(
    "total_sales",
    ascending=False
)

# Display the top 10 sellers by revenue
print("Top 10 Sellers by Revenue:")
print(seller_revenue.head(10).round(2))

# ==========================================
# 34. SELLER-WISE DELIVERY PERFORMANCE
# ==========================================

# Connect order items with delivery information
seller_delivery = order_items.merge(
    orders[["order_id", "delivery_performance"]],
    on="order_id",
    how="left"
)

# Keep only one record per seller per order
# This avoids counting the same seller-order combination twice
seller_delivery = seller_delivery.drop_duplicates(
    subset=["seller_id", "order_id"]
)

# Calculate unique orders and late-delivery percentage
seller_delivery_summary = (
    seller_delivery
    .groupby("seller_id")
    .agg(
        unique_orders=("order_id", "nunique"),
        late_delivery_percentage=(
            "delivery_performance",
            lambda x: (x == "Late").mean() * 100
        )
    )
    .reset_index()
)

# Round the percentage to two decimal places
seller_delivery_summary["late_delivery_percentage"] = (
    seller_delivery_summary["late_delivery_percentage"].round(2)
)

# Show the 10 sellers with the highest late-delivery percentage
print("Top 10 Sellers by Late Delivery Percentage:")

print(
    seller_delivery_summary
    .sort_values("late_delivery_percentage", ascending=False)
    .head(10)
)

# ==========================================
# 35. FILTER SELLERS WITH ENOUGH ORDERS
# ==========================================

# Keep sellers who handled at least 50 unique orders
reliable_sellers = seller_delivery_summary[
    seller_delivery_summary["unique_orders"] >= 50
].copy()

# Sort sellers by highest late-delivery percentage
reliable_sellers = reliable_sellers.sort_values(
    "late_delivery_percentage",
    ascending=False
)

# Display the top 10 sellers for further investigation
print("Top 10 Sellers with at Least 50 Orders:")
print(reliable_sellers.head(10))
