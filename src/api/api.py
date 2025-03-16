import os
import uuid
from datetime import datetime

import boto3
import psycopg2.extras
from boto3.dynamodb.types import TypeDeserializer
from fastapi import FastAPI, HTTPException, Query
from models.models import (
    Cart,
    CartDynamo,
    Customer,
    InventoryItem,
    InventoryItemResponse,
    Transaction,
    Vendor,
)
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

dynamodb = boto3.resource("dynamodb", "us-east-1")
nosql_table = dynamodb.Table("mercado_ecommerce")
deserializer = TypeDeserializer()


def dynamo_to_python(dynamo_item):
    """Converts a DynamoDB item to a standard Python dictionary."""
    return {k: deserializer.deserialize(v) for k, v in dynamo_item.items()}


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


@app.post("/inventory/", response_model=InventoryItemResponse)
def create_inventory(
    item: InventoryItem, vendor_id: int = Query(..., title="Vendor ID")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        updated_at_str = datetime.now().isoformat()  # Convert datetime to string
        cursor.execute(
            """
            INSERT INTO inventory (item_name, category, price, updated_at, vendor_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING *;
            """,
            (item.item_name, item.category, item.price, updated_at_str, vendor_id),
        )
        new_item = cursor.fetchone()
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return new_item


@app.post("/cart/")
def store_cart(cart: Cart):
    """Stores a user's cart in DynamoDB."""

    nosql_table.put_item(
        Item={
            "pk": f"USER#{cart.user_id}",
            "sk": "CART",
            "cart": [item.model_dump() for item in cart.cart],
            "updated_at": datetime.now().isoformat(),
        }
    )
    return cart


@app.post("/checkout/")
def checkout(transaction: Transaction):
    """Converts a cart into a transaction and clears the cart."""
    # Get Cart
    response = nosql_table.get_item(
        Key={
            "pk": f"USER#{transaction.user_id}",
            "sk": "CART",
        }
    )
    cart_data = response.get("Item")
    python_cart_dict = dynamo_to_python(cart_data)
    cart = CartDynamo(**python_cart_dict)

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    txn_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    sk = f"USER{transaction.user_id}#{timestamp}"

    # Store full cart in a single transaction
    nosql_table.put_item(
        Item={
            "pk": txn_id,
            "sk": sk,
            "cart": cart.cart,
            "created_at": timestamp,
        }
    )

    # Clear Cart
    nosql_table.delete_item(
        Key={
            "pk": f"USER#{transaction.user_id}",
            "sk": "CART",
        }
    )
    return {"message": "Transaction completed", "transaction_id": txn_id}
