# Digital warehouse Manager

## 1. Purpose

Digital warehouse Manager is a small web application that lets a mini sample warehouse manage its
products, customers, and orders, and view basic sales analytics — backed by a
SQLite database and real SQL queries (joins, aggregates, subqueries, transactions).

## 2. Technology used

- **Backend:** Python 3 with Flask
- **Database:** SQLite, accessed with Python's built-in `sqlite3` module (no ORM)
- **Frontend:** server-side Jinja2 HTML templates with plain CSS

## 3. Installing dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      
pip install -r requirements.txt
```

## 4. Creating / initializing the database

```bash
python3 database/generate_seed.py
python3 -c "
import sqlite3
conn = sqlite3.connect('database/store.db')
conn.executescript(open('database/schema.sql').read())
conn.executescript(open('database/seed.sql').read())
conn.commit()
conn.close()
print('Database created')
"
```

## 5. Running the application

```bash
cd src
python3 app.py
```

Open **http://127.0.0.1:5000** in your browser.

## 6. Main application pages

| Page | URL | Description |
|---|---|---|
| Dashboard | `/` | KPI cards, 5 most recent orders, best-selling product |
| Products | `/products` | Search, filter, sort, CRUD, low-stock warning |
| Customers | `/customers` | List with order count/total spent, detail view, create/delete |
| Orders | `/orders` | List, transactional order creation with stock checks |
| Analytics | `/analytics` | Revenue by category, top customers, never-ordered products, above-average orders, low stock, monthly sales |

## 7. Author

*Victor Battu*