"""
Sample E-Commerce database schema and dataset generator.
Works seamlessly across SQLite and PostgreSQL engines.
"""

from datetime import datetime, timedelta
import random
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, MetaData, Table
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    country = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    loyalty_tier = Column(String(20), default="Bronze")  # Bronze, Silver, Gold, Platinum
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    rating = Column(Float, default=4.0)
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), default="pending")  # pending, processing, shipped, delivered, cancelled
    total_amount = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=5.0)
    payment_method = Column(String(30), default="Credit Card")  # Credit Card, PayPal, Crypto, Bank Transfer


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def seed_sample_database(session):
    """Populates the database with realistic sample e-commerce data."""
    # Check if data already exists
    if session.query(Category).count() > 0:
        return

    random.seed(42)

    # 1. Categories
    categories_data = [
        ("Electronics", "Smartphones, laptops, monitors, accessories, and consumer gadgets"),
        ("Audio", "Headphones, wireless earbuds, bluetooth speakers, and soundbars"),
        ("Home & Kitchen", "Coffee makers, blenders, air fryers, cookware, and smart home appliances"),
        ("Apparel", "Men's and women's clothing, footwear, jackets, and accessories"),
        ("Fitness", "Yoga mats, dumbbells, smart fitness bands, water bottles, and resistance bands")
    ]
    categories = []
    for name, desc in categories_data:
        cat = Category(name=name, description=desc)
        session.add(cat)
        categories.append(cat)
    session.flush()

    # 2. Customers
    customers_data = [
        ("Alice", "Johnson", "alice.johnson@example.com", "USA", "New York", "Platinum"),
        ("Bob", "Smith", "bob.smith@example.com", "USA", "San Francisco", "Gold"),
        ("Clara", "Dupont", "clara.dupont@example.com", "France", "Paris", "Gold"),
        ("David", "Kim", "david.kim@example.com", "South Korea", "Seoul", "Silver"),
        ("Elena", "Rostova", "elena.rostova@example.com", "Germany", "Berlin", "Bronze"),
        ("Fiona", "MacLeod", "fiona.macleod@example.com", "UK", "London", "Platinum"),
        ("George", "Patel", "george.patel@example.com", "India", "Bengaluru", "Silver"),
        ("Hannah", "Mueller", "hannah.mueller@example.com", "Germany", "Munich", "Bronze"),
        ("Isaac", "Newton", "isaac.n@example.com", "UK", "Cambridge", "Gold"),
        ("Julia", "Santos", "julia.s@example.com", "Brazil", "Sao Paulo", "Bronze"),
        ("Liam", "O'Connor", "liam.oc@example.com", "Ireland", "Dublin", "Silver"),
        ("Maya", "Lin", "maya.lin@example.com", "Canada", "Vancouver", "Platinum")
    ]
    customers = []
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    for i, (fn, ln, email, country, city, tier) in enumerate(customers_data):
        cust = Customer(
            first_name=fn,
            last_name=ln,
            email=email,
            country=country,
            city=city,
            loyalty_tier=tier,
            created_at=base_time + timedelta(days=i * 12)
        )
        session.add(cust)
        customers.append(cust)
    session.flush()

    # 3. Products
    products_data = [
        # Electronics
        ("ProBook X15 Laptop", 1, 1299.99, 45, 4.8),
        ("UltraView 27-inch 4K Monitor", 1, 389.50, 30, 4.6),
        ("ErgoClick Wireless Mouse", 1, 49.99, 120, 4.3),
        ("MechKey RGB Mechanical Keyboard", 1, 119.00, 60, 4.7),
        ("USB-C Fast Charging Hub 100W", 1, 35.99, 200, 4.5),
        # Audio
        ("NoiseCancel Studio Over-Ear Headphones", 2, 249.99, 85, 4.9),
        ("AirBeats True Wireless Earbuds", 2, 89.99, 150, 4.4),
        ("BoomBox Waterproof Bluetooth Speaker", 2, 69.99, 90, 4.5),
        ("SoundPulse TV Soundbar 120W", 2, 179.99, 40, 4.2),
        # Home & Kitchen
        ("BaristaMax Espresso Machine", 3, 449.99, 25, 4.8),
        ("SmartAir Digital Air Fryer 6L", 3, 99.99, 70, 4.6),
        ("TurboBlend High-Speed Blender", 3, 79.99, 50, 4.1),
        ("ChefElite 12-Piece Ceramic Cookware", 3, 149.99, 35, 4.7),
        # Apparel
        ("All-Weather Waterproof Jacket", 4, 129.99, 80, 4.5),
        ("Classic Organic Cotton Crewneck", 4, 34.50, 220, 4.3),
        ("FlexFit Running Sneakers", 4, 95.00, 65, 4.6),
        ("Thermal Fleece Travel Hoodie", 4, 59.99, 110, 4.4),
        # Fitness
        ("EcoGrip Non-Slip Yoga Mat 6mm", 5, 29.99, 140, 4.7),
        ("Adjustable Cast Iron Dumbbell Pair 20kg", 5, 119.99, 40, 4.8),
        ("PulseFit GPS Smart Activity Tracker", 5, 89.99, 75, 4.2),
        ("HydraSteel Vacuum Insulated Bottle 1L", 5, 24.99, 250, 4.9)
    ]
    products = []
    for name, cat_idx, price, stock, rating in products_data:
        prod = Product(
            name=name,
            category_id=cat_idx,
            price=price,
            stock_quantity=stock,
            rating=rating,
            is_active=True
        )
        session.add(prod)
        products.append(prod)
    session.flush()

    # 4. Orders and Order Items
    order_statuses = ["delivered", "delivered", "delivered", "shipped", "processing", "pending", "cancelled"]
    payment_methods = ["Credit Card", "Credit Card", "PayPal", "Apple Pay", "Bank Transfer"]

    order_dates = [
        datetime(2024, 2, 1) + timedelta(days=i * 7, hours=(i * 3) % 24)
        for i in range(25)
    ]

    for i, odate in enumerate(order_dates):
        customer = customers[i % len(customers)]
        status = order_statuses[i % len(order_statuses)]
        payment = payment_methods[i % len(payment_methods)]
        shipping = 0.0 if i % 2 == 0 else 9.99

        order = Order(
            customer_id=customer.id,
            order_date=odate,
            status=status,
            total_amount=0.0,
            shipping_fee=shipping,
            payment_method=payment
        )
        session.add(order)
        session.flush()

        # Add 1 to 4 items per order
        num_items = 1 + (i % 3)
        order_total = 0.0
        used_products = set()

        for j in range(num_items):
            prod_idx = (i * 3 + j * 5) % len(products)
            if prod_idx in used_products:
                prod_idx = (prod_idx + 1) % len(products)
            used_products.add(prod_idx)

            product = products[prod_idx]
            qty = 1 if product.price > 200 else (1 + (j % 2))
            unit_price = product.price

            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price
            )
            session.add(item)
            order_total += (qty * unit_price)

        order.total_amount = round(order_total + shipping, 2)
        session.flush()

    # 5. Reviews
    sample_reviews = [
        (1, 1, 5, "Remarkable build quality and blazing fast processing speed."),
        (2, 2, 4, "Great 4K clarity for coding and productivity. Stand could be sturdier."),
        (6, 3, 5, "Active noise cancelling is top tier. Best travel headphones I've owned."),
        (10, 6, 5, "Cafe quality espresso at home. Easy to clean and dial in."),
        (11, 4, 4, "Crispy fries with zero oil guilt. Cooks super fast!"),
        (18, 5, 5, "Extremely sturdy dumbbells with a smooth knurling grip."),
        (21, 12, 5, "Keeps iced water freezing cold even after 24 hours in the car.")
    ]
    for prod_id, cust_id, rating, comment in sample_reviews:
        rev = Review(
            product_id=prod_id,
            customer_id=cust_id,
            rating=rating,
            comment=comment,
            created_at=datetime(2024, 3, 10, 14, 30)
        )
        session.add(rev)

    session.commit()

