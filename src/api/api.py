import os

import psycopg2.extras
from fastapi import FastAPI, HTTPException
from models.models import Customer
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
                customer.joined_at,
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
