import os

import psycopg2
from fastapi import FastAPI, Query
from models.models import Customer, InventoryItem, Vendor
from psycopg2.extras import RealDictCursor

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
HOST = os.getenv("HOST")

# Construct the DATABASE_URL
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{HOST}:5432/{POSTGRES_DB}"
)
app = FastAPI()


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


@app.post("/customers/")
def create_customer(customer: Customer):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customer (first_name, last_name, email, joined_at)"
        " VALUES (%s, %s, %s, %s) RETURNING *",
        (customer.first_name, customer.last_name, customer.email, customer.joined_at),
    )
    new_customer = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return new_customer


@app.post("/vendors/")
def create_vendor(vendor: Vendor):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vendor (vendor_name, region, joined_at) VALUES (%s, %s, %s) RETURNING *",
        (vendor.vendor_name, vendor.region, vendor.joined_at),
    )
    new_vendor = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return new_vendor


@app.post("/inventory/")
def create_inventory(item: InventoryItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventory (item_name, category, price, updated_at, vendor_id) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (item.item_name, item.category, item.price, item.updated_at, item.vendor_id),
    )
    new_item = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return new_item


@app.get("/inventory/")
def get_inventory(item_name: str = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()
    if item_name:
        cursor.execute(
            "SELECT * FROM inventory WHERE item_name ILIKE %s", (f"%{item_name}%",)
        )
    else:
        cursor.execute("SELECT * FROM inventory")
    inventory = cursor.fetchall()
    cursor.close()
    conn.close()
    return inventory


@app.get("/vendors/{vendor_id}/inventory")
def get_vendor_inventory(vendor_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE vendor_id = %s", (vendor_id,))
    vendor_inventory = cursor.fetchall()
    cursor.close()
    conn.close()
    return vendor_inventory
