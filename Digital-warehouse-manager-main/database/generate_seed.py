import random
from datetime import datetime, timedelta

random.seed(42)  # same data every time you regenerate

categories = [
    ("Beverages", "Drinks, coffee, tea and juices"),
    ("Bakery", "Bread, pastries and cakes"),
    ("Dairy", "Milk, cheese and yogurt"),
    ("Snacks", "Chips, biscuits and sweets"),
    ("Household", "Cleaning and home essentials"),
]

# (name, category_index 1-5, price, stock)
products = [
    ("Sparkling Water 1.5L", 1, 1.10, 80),
    ("Cold Brew Coffee 330ml", 1, 2.80, 25),
    ("Sourdough Bread", 2, 3.40, 15),
    ("Croissant (pack of 4)", 2, 4.20, 3),
    ("Chocolate Muffin", 2, 1.90, 20),
    ("Baguette", 2, 1.20, 30),
    ("Greek Yogurt 500g", 3, 2.90, 2),
    ("Cheddar Cheese 200g", 3, 3.60, 18),
    ("Butter 250g", 3, 2.40, 2),
    ("Mozzarella 125g", 3, 2.10, 27),
    ("Potato Chips 150g", 4, 2.00, 45),
    ("Dark Chocolate Bar", 4, 2.60, 33),
    ("Green Tea Box (20 bags)", 1, 3.50, 60),
    ("Almonds 200g", 4, 4.80, 12),
    ("Digestive Biscuits", 4, 1.80, 3),
    ("Dish Soap 500ml", 5, 2.30, 28),
    ("Cinnamon Roll", 2, 2.50, 4),
    ("Espresso Beans 250g", 1, 8.90, 40),
    ("Orange Juice 1L", 1, 2.20, 35),
    ("Whole Milk 1L", 3, 1.30, 50),
]

first_names = ["Alice", "Bruno", "Chloe", "David", "Emma", "Farid",
               "Gabrielle", "Hugo", "Ines", "Julien", "Karim", "Lea"]
last_names = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Petit",
              "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Michel"]
cities = ["Paris", "Lyon", "Marseille", "Toulouse", "Nantes", "Lille"]

customers = []
for i in range(12):
    fn, ln = first_names[i], last_names[i]
    email = f"{fn.lower()}.{ln.lower()}@example.com"
    city = random.choice(cities)
    days_ago = random.randint(30, 400)
    created = (datetime(2026, 8, 20) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
    customers.append((fn, ln, email, city, created))

statuses = ["pending", "paid", "shipped", "cancelled"]
status_weights = [0.15, 0.35, 0.4, 0.10]

months = [(2026, m) for m in range(3, 9)]  # March through August 2026
orders = []
for order_id in range(1, 26):
    customer_id = random.randint(1, 12)
    year, month = months[(order_id - 1) % len(months)]
    day = random.randint(1, 27)
    order_date = f"{year:04d}-{month:02d}-{day:02d} {random.randint(9,19):02d}:{random.randint(0,59):02d}:00"
    status = random.choices(statuses, weights=status_weights, k=1)[0]
    orders.append((customer_id, order_date, status))

order_items = []
remaining = 50
order_indices = list(range(1, 26))

items_per_order = {oid: 1 for oid in order_indices}  # everyone starts with 1
remaining -= 25

while remaining > 0:
    oid = random.choice(order_indices)
    if items_per_order[oid] < 3:
        items_per_order[oid] += 1
        remaining -= 1

for order_id in order_indices:
    used_products = random.sample(range(1, 21), items_per_order[order_id])
    for product_id in used_products:
        quantity = random.randint(1, 5)
        unit_price = products[product_id - 1][2]  # snapshot the current price
        order_items.append((order_id, product_id, quantity, unit_price))


lines = ["-- Mini Store Manager - Seed Data", ""]

lines.append("INSERT INTO Category (name, description) VALUES")
lines.append(",\n".join(f"    ('{n}', '{d}')" for n, d in categories) + ";")
lines.append("")

lines.append("INSERT INTO Product (name, description, price, stock, category_id) VALUES")
rows = [f"    ('{name}', '{name} - quality item', {price}, {stock}, {cat_id})"
        for name, cat_id, price, stock in products]
lines.append(",\n".join(rows) + ";")
lines.append("")

lines.append("INSERT INTO Customer (first_name, last_name, email, city, created_at) VALUES")
rows = [f"    ('{fn}', '{ln}', '{email}', '{city}', '{created}')"
        for fn, ln, email, city, created in customers]
lines.append(",\n".join(rows) + ";")
lines.append("")

lines.append("INSERT INTO CustomerOrder (customer_id, order_date, status) VALUES")
rows = [f"    ({cid}, '{date}', '{status}')" for cid, date, status in orders]
lines.append(",\n".join(rows) + ";")
lines.append("")

lines.append("INSERT INTO OrderItem (order_id, product_id, quantity, unit_price) VALUES")
rows = [f"    ({oid}, {pid}, {qty}, {price})" for oid, pid, qty, price in order_items]
lines.append(",\n".join(rows) + ";")
lines.append("")

with open("database/seed.sql", "w") as f:
    f.write("\n".join(lines))

print("seed.sql written")