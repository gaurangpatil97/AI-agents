import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

products = {
    "Laptop": ("Electronics", 999),
    "Phone": ("Electronics", 699),
    "Headphones": ("Electronics", 199),
    "T-Shirt": ("Clothing", 29),
    "Jeans": ("Clothing", 59),
    "Sneakers": ("Footwear", 89),
    "Watch": ("Accessories", 149),
    "Backpack": ("Accessories", 79),
}

regions = ["North", "South", "East", "West"]
age_groups = ["18-25", "26-35", "36-45", "46+"]

rows = []
start_date = datetime(2022, 1, 1)

for _ in range(2000):
    date = start_date + timedelta(days=random.randint(0, 365*3))
    product = random.choice(list(products.keys()))
    category, base_price = products[product]
    region = random.choice(regions)
    age_group = random.choice(age_groups)
    units = random.randint(1, 20)
    price = round(base_price * random.uniform(0.9, 1.1), 2)
    total = round(units * price, 2)

    rows.append({
        "Date": date.strftime("%Y-%m-%d"),
        "Product": product,
        "Category": category,
        "Region": region,
        "Age Group": age_group,
        "Units Sold": units,
        "Unit Price": price,
        "Total Sales": total
    })

df = pd.DataFrame(rows)
df.to_csv("sales_data.csv", index=False)
print(f"✅ Dataset created! {len(df)} rows")
print(df.head())