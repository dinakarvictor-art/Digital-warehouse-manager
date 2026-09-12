import sqlite3
from flask import Flask, render_template
from db import get_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


@app.route("/")
def dashboard():
    db = get_db()

    product_count = db.execute("SELECT COUNT(*) AS c FROM Product").fetchone()["c"]
    customer_count = db.execute("SELECT COUNT(*) AS c FROM Customer").fetchone()["c"]
    order_count = db.execute("SELECT COUNT(*) AS c FROM CustomerOrder").fetchone()["c"]

    total_revenue = db.execute("""
        SELECT COALESCE(SUM(quantity * unit_price), 0) AS revenue
        FROM OrderItem
    """).fetchone()["revenue"]

    recent_orders = db.execute("""
        SELECT o.id, c.first_name || ' ' || c.last_name AS customer_name,
               o.order_date, o.status,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM CustomerOrder o
        JOIN Customer c ON c.id = o.customer_id
        LEFT JOIN OrderItem oi ON oi.order_id = o.id
        GROUP BY o.id
        ORDER BY o.order_date DESC
        LIMIT 5
    """).fetchall()

    best_seller = db.execute("""
        SELECT p.name, SUM(oi.quantity) AS total_qty
        FROM OrderItem oi
        JOIN Product p ON p.id = oi.product_id
        GROUP BY p.id
        ORDER BY total_qty DESC
        LIMIT 1
    """).fetchone()

    db.close()
    return render_template(
        "dashboard.html",
        product_count=product_count,
        customer_count=customer_count,
        order_count=order_count,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
        best_seller=best_seller,
    )

from flask import Flask, render_template, request, redirect, url_for, flash

@app.route("/products")
def products():
    db = get_db()
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", "")
    sort = request.args.get("sort", "name")

    sort_column = {"name": "p.name", "price": "p.price"}.get(sort, "p.name")

    query = f"""
        SELECT p.id, p.name, p.price, p.stock, c.name AS category_name
        FROM Product p
        JOIN Category c ON c.id = p.category_id
        WHERE p.name LIKE ?
          AND (? = '' OR p.category_id = ?)
        ORDER BY {sort_column} ASC
    """
    rows = db.execute(query, (f"%{search}%", category_id, category_id)).fetchall()
    categories = db.execute("SELECT * FROM Category ORDER BY name").fetchall()
    db.close()

    return render_template(
        "products.html", products=rows, categories=categories,
        search=search, category_id=category_id, sort=sort,
    )

@app.route("/products/create", methods=["GET", "POST"])
def product_create():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        price = request.form["price"]
        stock = request.form["stock"]
        category_id = request.form["category_id"]

        error = None
        try:
            price_val = float(price)
            stock_val = int(stock)
            if price_val < 0 or stock_val < 0:
                error = "Price and stock cannot be negative."
        except ValueError:
            error = "Price and stock must be valid numbers."

        if error:
            flash(error)
            categories = db.execute("SELECT * FROM Category ORDER BY name").fetchall()
            db.close()
            return render_template("product_form.html", categories=categories, product=request.form)

        db.execute(
            "INSERT INTO Product (name, description, price, stock, category_id) VALUES (?, ?, ?, ?, ?)",
            (name, description, price_val, stock_val, category_id),
        )
        db.commit()
        db.close()
        return redirect(url_for("products"))

    categories = db.execute("SELECT * FROM Category ORDER BY name").fetchall()
    db.close()
    return render_template("product_form.html", categories=categories, product=None)


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        price = request.form["price"]
        stock = request.form["stock"]
        category_id = request.form["category_id"]

        error = None
        try:
            price_val = float(price)
            stock_val = int(stock)
            if price_val < 0 or stock_val < 0:
                error = "Price and stock cannot be negative."
        except ValueError:
            error = "Price and stock must be valid numbers."

        if error:
            flash(error)
            categories = db.execute("SELECT * FROM Category ORDER BY name").fetchall()
            db.close()
            return render_template("product_form.html", categories=categories,
                                    product={"id": product_id, **request.form})

        db.execute(
            "UPDATE Product SET name=?, description=?, price=?, stock=?, category_id=? WHERE id=?",
            (name, description, price_val, stock_val, category_id, product_id),
        )
        db.commit()
        db.close()
        return redirect(url_for("products"))

    product = db.execute("SELECT * FROM Product WHERE id = ?", (product_id,)).fetchone()
    categories = db.execute("SELECT * FROM Category ORDER BY name").fetchall()
    db.close()
    return render_template("product_form.html", categories=categories, product=product)


@app.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    db = get_db()
    try:
        db.execute("DELETE FROM Product WHERE id = ?", (product_id,))
        db.commit()
    except sqlite3.IntegrityError:
        flash("Cannot delete this product: it is referenced by existing orders.")
    finally:
        db.close()
    return redirect(url_for("products"))

@app.route("/customers")
def customers():
    db = get_db()
    search = request.args.get("search", "").strip()

    rows = db.execute("""
        SELECT c.id, c.first_name, c.last_name, c.email, c.city,
               COUNT(DISTINCT o.id) AS order_count,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
        FROM Customer c
        LEFT JOIN CustomerOrder o ON o.customer_id = c.id
        LEFT JOIN OrderItem oi ON oi.order_id = o.id
        WHERE (c.first_name || ' ' || c.last_name) LIKE ?
        GROUP BY c.id
        ORDER BY c.last_name
    """, (f"%{search}%",)).fetchall()
    db.close()
    return render_template("customers.html", customers=rows, search=search)


@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    db = get_db()
    customer = db.execute("SELECT * FROM Customer WHERE id = ?", (customer_id,)).fetchone()
    if customer is None:
        db.close()
        flash("Customer not found.")
        return redirect(url_for("customers"))

    orders = db.execute("""
        SELECT o.id, o.order_date, o.status,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM CustomerOrder o
        LEFT JOIN OrderItem oi ON oi.order_id = o.id
        WHERE o.customer_id = ?
        GROUP BY o.id
        ORDER BY o.order_date DESC
    """, (customer_id,)).fetchall()

    total_spent = db.execute("""
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM CustomerOrder o
        JOIN OrderItem oi ON oi.order_id = o.id
        WHERE o.customer_id = ?
    """, (customer_id,)).fetchone()["total"]

    db.close()
    return render_template("customer_detail.html", customer=customer, orders=orders, total_spent=total_spent)

@app.route("/customers/create", methods=["GET", "POST"])
def customer_create():
    db = get_db()
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        email = request.form["email"].strip()
        city = request.form.get("city", "").strip()

        try:
            db.execute(
                "INSERT INTO Customer (first_name, last_name, email, city) VALUES (?, ?, ?, ?)",
                (first_name, last_name, email, city),
            )
            db.commit()
            db.close()
            return redirect(url_for("customers"))
        except sqlite3.IntegrityError:
            flash("A customer with this email already exists.")
            db.close()
            return render_template("customer_form.html", form=request.form)

    db.close()
    return render_template("customer_form.html", form=None)


@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
def customer_delete(customer_id):
    db = get_db()
    try:
        db.execute("DELETE FROM Customer WHERE id = ?", (customer_id,))
        db.commit()
    except sqlite3.IntegrityError:
        flash("Cannot delete this customer: they have existing orders.")
    finally:
        db.close()
    return redirect(url_for("customers"))


@app.route("/orders")
def orders():
    db = get_db()
    rows = db.execute("""
        SELECT o.id, c.first_name || ' ' || c.last_name AS customer_name,
               o.order_date, o.status,
               COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total
        FROM CustomerOrder o
        JOIN Customer c ON c.id = o.customer_id
        LEFT JOIN OrderItem oi ON oi.order_id = o.id
        GROUP BY o.id
        ORDER BY o.order_date DESC
    """).fetchall()
    db.close()
    return render_template("orders.html", orders=rows)
@app.route("/orders/<int:order_id>")
def order_detail(order_id):
    db = get_db()
    order = db.execute("""
        SELECT o.id, o.order_date, o.status, c.id AS customer_id,
               c.first_name || ' ' || c.last_name AS customer_name, c.email
        FROM CustomerOrder o
        JOIN Customer c ON c.id = o.customer_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if order is None:
        db.close()
        flash("Order not found.")
        return redirect(url_for("orders"))

    items = db.execute("""
        SELECT oi.id, p.name AS product_name, oi.quantity, oi.unit_price,
               (oi.quantity * oi.unit_price) AS line_total
        FROM OrderItem oi
        JOIN Product p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    order_total = sum(item["line_total"] for item in items)
    db.close()
    return render_template("order_detail.html", order=order, items=items, order_total=order_total)

@app.route("/orders/create", methods=["GET", "POST"])
def order_create():
    db = get_db()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        product_ids = request.form.getlist("product_id")
        quantities = request.form.getlist("quantity")

        cart = []
        for pid, qty in zip(product_ids, quantities):
            if pid and qty and int(qty) > 0:
                cart.append((int(pid), int(qty)))

        if not customer_id or not cart:
            flash("Select a customer and at least one product with a quantity.")
            db.close()
            return redirect(url_for("order_create"))

        try:
            db.execute("BEGIN")
            cur = db.execute(
                "INSERT INTO CustomerOrder (customer_id, status) VALUES (?, 'pending')",
                (customer_id,),
            )
            new_order_id = cur.lastrowid

            for product_id, quantity in cart:
                product = db.execute(
                    "SELECT price, stock FROM Product WHERE id = ?", (product_id,)
                ).fetchone()
                if product is None:
                    raise ValueError(f"Product {product_id} does not exist.")
                if product["stock"] < quantity:
                    raise ValueError(f"Insufficient stock for product {product_id}.")

                db.execute(
                    "INSERT INTO OrderItem (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (new_order_id, product_id, quantity, product["price"]),
                )
                db.execute(
                    "UPDATE Product SET stock = stock - ? WHERE id = ?",
                    (quantity, product_id),
                )

            db.commit()
            flash(f"Order #{new_order_id} created successfully.")
            db.close()
            return redirect(url_for("order_detail", order_id=new_order_id))

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            db.close()
            flash(f"Order could not be created: {e}")
            return redirect(url_for("order_create"))

    customers_list = db.execute("SELECT id, first_name, last_name FROM Customer ORDER BY last_name").fetchall()
    products_list = db.execute("SELECT id, name, price, stock FROM Product ORDER BY name").fetchall()
    db.close()
    return render_template("order_form.html", customers=customers_list, products=products_list)

@app.route("/analytics")
def analytics():
    db = get_db()

    # A - Revenue by category
    revenue_by_category = db.execute("""
        SELECT c.name AS category_name,
               SUM(oi.quantity) AS units_sold,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM OrderItem oi
        JOIN Product p ON p.id = oi.product_id
        JOIN Category c ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY revenue DESC
    """).fetchall()

    # B - Top 5 customers
    top_customers = db.execute("""
        SELECT cu.first_name || ' ' || cu.last_name AS customer_name,
               SUM(oi.quantity * oi.unit_price) AS total_spent,
               COUNT(DISTINCT o.id) AS order_count
        FROM Customer cu
        JOIN CustomerOrder o ON o.customer_id = cu.id
        JOIN OrderItem oi ON oi.order_id = o.id
        GROUP BY cu.id
        ORDER BY total_spent DESC
        LIMIT 5
    """).fetchall()

    # C - Products never ordered (LEFT JOIN ... IS NULL)
    never_ordered = db.execute("""
        SELECT p.id, p.name
        FROM Product p
        LEFT JOIN OrderItem oi ON oi.product_id = p.id
        WHERE oi.id IS NULL
    """).fetchall()

    # D - Orders above average order value (CTE + subquery)
    above_average_orders = db.execute("""
        WITH OrderTotals AS (
            SELECT o.id, o.order_date,
                   c.first_name || ' ' || c.last_name AS customer_name,
                   SUM(oi.quantity * oi.unit_price) AS total
            FROM CustomerOrder o
            JOIN Customer c ON c.id = o.customer_id
            JOIN OrderItem oi ON oi.order_id = o.id
            GROUP BY o.id
        )
        SELECT id, order_date, customer_name, total
        FROM OrderTotals
        WHERE total > (SELECT AVG(total) FROM OrderTotals)
        ORDER BY total DESC
    """).fetchall()

    avg_order_value = db.execute("""
        SELECT AVG(order_total) AS avg_value FROM (
            SELECT SUM(oi.quantity * oi.unit_price) AS order_total
            FROM CustomerOrder o
            JOIN OrderItem oi ON oi.order_id = o.id
            GROUP BY o.id
        )
    """).fetchone()["avg_value"]

    # E - Low stock products
    low_stock = db.execute("""
        SELECT id, name, stock FROM Product WHERE stock < 5 ORDER BY stock ASC
    """).fetchall()

    # F - Sales by month
    sales_by_month = db.execute("""
        SELECT strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM CustomerOrder o
        JOIN OrderItem oi ON oi.order_id = o.id
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()

    db.close()
    return render_template(
        "analytics.html",
        revenue_by_category=revenue_by_category,
        top_customers=top_customers,
        never_ordered=never_ordered,
        above_average_orders=above_average_orders,
        avg_order_value=avg_order_value,
        low_stock=low_stock,
        sales_by_month=sales_by_month,
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)