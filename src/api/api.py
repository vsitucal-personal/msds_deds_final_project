import os
from datetime import datetime

import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from models.models import Customer, CustomerResponse, Vendor
from psycopg2 import IntegrityError
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


@app.post("/customers/", status_code=201)
def create_customer(customer: Customer):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO customer (first_name, last_name, email, joined_at)
            VALUES (%s, %s, %s, %s) RETURNING *;
            """,
            (
                customer.first_name,
                customer.last_name,
                customer.email,
                datetime.now().isoformat(),
            ),
        )
        new_customer = cursor.fetchone()
        conn.commit()
    except IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        cursor.close()
        conn.close()

    return new_customer


@app.get("/customers/", response_model=CustomerResponse)
def get_customer(
    email: str = Query(
        ..., title="Customer Email", description="Email of the customer to retrieve"
    )
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM customer WHERE email = %s;", (email,))
        customer = cursor.fetchone()
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    finally:
        cursor.close()
        conn.close()

    return customer


@app.post("/vendors/", status_code=201)
def register_vendor(vendor: Vendor):
    """Registers a new vendor in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO vendor (vendor_name, region, joined_at)
            VALUES (%s, %s, %s) RETURNING *;
            """,
            (vendor.vendor_name, vendor.region, datetime.now().isoformat()),
        )
        new_vendor = cursor.fetchone()
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Vendor registration failed")
    finally:
        cursor.close()
        conn.close()

    return new_vendor


@app.get("/vendors/")
def get_vendor_by_name(vendor_name: str = Query(..., title="Vendor Name")):
    """Fetches a vendor by name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM vendor WHERE vendor_name = %s;", (vendor_name,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
    finally:
        cursor.close()
        conn.close()

    return vendor
