import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

products = ['Laptop', 'Phone', 'Headphones', 'T-Shirt', 'Jeans', 'Sneakers', 'Watch', 'Backpack']
categories = {
    'Laptop': 'Electronics', 'Phone': 'Electronics', 'Headphones': 'Electronics',
    'T-Shirt': 'Clothing', 'Jeans': 'Clothing', 'Sneakers': 'Footwear',
    'Watch': 'Accessories', 'Backpack': 'Accessories'
}
regions = ['North', 'South', 'East', 'West']

# ── INVENTORY DATA ──────────────────────────────────────────
reorder_points = {
    'Laptop': 30, 'Phone': 50, 'Headphones': 40,
    'T-Shirt': 100, 'Jeans': 80, 'Sneakers': 60,
    'Watch': 35, 'Backpack': 45
}
warehouse_costs = {
    'Laptop': 120, 'Phone': 80, 'Headphones': 25,
    'T-Shirt': 5, 'Jeans': 8, 'Sneakers': 15,
    'Watch': 30, 'Backpack': 12
}

inventory_rows = []
start = datetime(2022, 1, 1)
months = pd.date_range(start='2022-01-01', end='2024-12-31', freq='MS')

for month in months:
    for product in products:
        for region in regions:
            stock = random.randint(20, 200)
            received = random.randint(50, 300)
            cost = warehouse_costs[product] * stock * random.uniform(0.9, 1.1)
            inventory_rows.append({
                'Date': month.strftime('%Y-%m-%d'),
                'Product': product,
                'Category': categories[product],
                'Region': region,
                'Stock_Level': stock,
                'Reorder_Point': reorder_points[product],
                'Units_Received': received,
                'Warehouse_Cost': round(cost, 2)
            })

inventory_df = pd.DataFrame(inventory_rows)
inventory_df.to_csv('inventory_data.csv', index=False)
print(f"✅ inventory_data.csv — {len(inventory_df)} rows")

# ── CUSTOMER DATA ───────────────────────────────────────────
age_groups = ['18-25', '26-35', '36-45', '46+']
loyalty_tiers = ['Bronze', 'Silver', 'Gold', 'Platinum']
preferred_categories = ['Electronics', 'Clothing', 'Footwear', 'Accessories']

customer_rows = []
for i in range(1, 2001):
    region = random.choice(regions)
    age_group = random.choice(age_groups)
    preferred_cat = random.choice(preferred_categories)
    total_purchases = random.randint(1, 80)
    total_spent = round(total_purchases * random.uniform(50, 800), 2)
    loyalty_score = round(random.uniform(1, 10), 1)
    
    last_purchase = datetime(2022, 1, 1) + timedelta(days=random.randint(0, 1095))
    
    customer_rows.append({
        'Customer_ID': f'CUST{i:04d}',
        'Age_Group': age_group,
        'Region': region,
        'Preferred_Category': preferred_cat,
        'Total_Purchases': total_purchases,
        'Total_Spent': total_spent,
        'Last_Purchase_Date': last_purchase.strftime('%Y-%m-%d'),
        'Loyalty_Score': loyalty_score
    })

customer_df = pd.DataFrame(customer_rows)
customer_df.to_csv('customer_data.csv', index=False)
print(f"✅ customer_data.csv — {len(customer_df)} rows")

print("\nDone! Both datasets saved to backend folder.")