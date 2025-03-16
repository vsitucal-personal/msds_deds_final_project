from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO

import boto3
import pandas as pd
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.redshift_sql import RedshiftSQLHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow import DAG

# Replace with your S3 bucket name
S3_BUCKET = "mercado-ecommerce"
RAW_PREFIX = "raw/"
CLEAN_PREFIX = "clean/"
WORK_PREFIX = "work/"
GOLD_PREFIX = "gold/"


def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def list_tables():
    tables = ["customer", "vendor", "inventory"]
    return tables


def list_tables_redshift():
    tables = ["category", "customer", "date", "inventory", "sales", "vendor"]
    return tables


def upload_to_s3(df, s3_hook, today_str, file_format, buffer, prefix, table_name):
    """Handles the upload of a DataFrame to S3 with dynamic table names."""
    if file_format == "csv":
        df.to_csv(buffer, index=False)
        data = buffer.getvalue()
        upload_func = s3_hook.load_string
    else:  # Parquet
        df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
        data = buffer.getvalue()
        upload_func = s3_hook.load_bytes

    # Upload to S3 with dynamic key naming
    s3_key = f"{prefix}{table_name}/{today_str}/{table_name}.{file_format}"
    upload_func(data, key=s3_key, bucket_name=S3_BUCKET, replace=True)
    print(f"Uploaded {table_name}.{file_format} to s3://{S3_BUCKET}/{s3_key}")


def fetch_ddb_then_upload_():
    dynamodb = boto3.resource("dynamodb", "us-east-1")
    table = dynamodb.Table("mercado_ecommerce")

    filtered_items = [
        item for item in table.scan()["Items"] if item.get("sk") != "CART"
    ]
    df = pd.DataFrame(filtered_items)
    df = df.explode("cart")  # Expand each cart item into its own row

    # Convert cart dictionary to separate columns
    cart_df = pd.json_normalize(
        df["cart"].apply(lambda x: {k: convert_decimal(v) for k, v in x.items()})
    )

    # Merge with original DataFrame and drop the old cart column
    df = df.drop(columns=["cart"]).reset_index(drop=True)
    df = pd.concat([df, cart_df], axis=1)

    df["customer_id"] = (
        df["sk"].str.split("#").str[0].str.replace("USER", "", regex=False)
    )

    # Convert timestamp to datetime and extract date_id
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["date_id"] = df["created_at"].dt.strftime("%Y%m%d")

    category_df = pd.DataFrame({"category_id": [1], "category_name": ["General"]})
    df["category_id"] = category_df.loc[0, "category_id"]

    # Create a separate date DataFrame
    date_df = df[["date_id"]].drop_duplicates().copy()
    date_df["year"] = df["created_at"].dt.year
    date_df["month"] = df["created_at"].dt.month
    date_df["day"] = df["created_at"].dt.day

    df = df.drop(columns=["sk", "pk", "created_at"]).reset_index(drop=True)

    df = df[
        [
            "item_id",
            "customer_id",
            "vendor_id",
            "category_id",
            "date_id",
            "unit_price",
            "qty",
            "total_price",
        ]
    ]
    date_df = date_df[["date_id", "year", "month", "day"]]

    s3_hook = S3Hook(aws_conn_id="aws_default")

    zones = {
        "raw": ("csv", StringIO(), RAW_PREFIX),
        "clean": ("parquet", BytesIO(), CLEAN_PREFIX),
        "work": ("parquet", BytesIO(), WORK_PREFIX),
        "gold": ("parquet", BytesIO(), GOLD_PREFIX),
    }

    today_str = datetime.today().strftime("%Y%m%d")

    for zone, (file_format, buffer, prefix) in zones.items():
        upload_to_s3(df, s3_hook, today_str, file_format, buffer, prefix, "sales")
        upload_to_s3(
            category_df, s3_hook, today_str, file_format, buffer, prefix, "category"
        )
        upload_to_s3(date_df, s3_hook, today_str, file_format, buffer, prefix, "date")


def fetch_table_data_and_upload(table_name):
    # Connect to PostgreSQL
    hook = PostgresHook(postgres_conn_id="ecommerce")
    conn = hook.get_conn()
    cursor = conn.cursor()

    # Fetch table data
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]

    # Convert data to Pandas DataFrame
    df = pd.DataFrame(rows, columns=column_names)
    df = df.rename(columns={"id": f"{table_name}_id"})

    # Initialize S3 Hook
    s3_hook = S3Hook(aws_conn_id="aws_default")

    zones = {
        "raw": ("csv", StringIO(), RAW_PREFIX),
        "clean": ("parquet", BytesIO(), CLEAN_PREFIX),
        "work": ("parquet", BytesIO(), WORK_PREFIX),
        "gold": ("parquet", BytesIO(), GOLD_PREFIX),
    }

    today_str = datetime.today().strftime("%Y%m%d")

    for zone, (file_format, buffer, prefix) in zones.items():
        # Convert DataFrame to the appropriate format
        if file_format == "csv":
            df.to_csv(buffer, index=False)
            data = buffer.getvalue()
            upload_func = s3_hook.load_string
        else:  # parquet
            df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
            data = buffer.getvalue()
            upload_func = s3_hook.load_bytes

        # Upload to S3
        s3_key = f"{prefix}{table_name}/{today_str}/{table_name}.{file_format}"
        upload_func(data, key=s3_key, bucket_name=S3_BUCKET, replace=True)
        print(f"Uploaded {table_name}.{file_format} to s3://{S3_BUCKET}/{s3_key}")

    # Close DB connection
    cursor.close()
    conn.close()


def load_gold_to_redshift(table_name):
    s3_hook = S3Hook(aws_conn_id="aws_default")

    # List all folders under the table's S3 path
    table_path = f"{GOLD_PREFIX}{table_name}/"
    folders = s3_hook.list_keys(bucket_name=S3_BUCKET, prefix=table_path)

    print(folders)
    print([key.split("/")[-2] for key in folders])

    # Extract available date folders and sort them
    date_folders = [
        key.split("/")[-2]
        for key in folders
        if key.split("/")[-2].isdigit() and len(key.split("/")[-2]) == 8
    ]

    if not date_folders:
        raise ValueError(f"No date folders found in {table_path}")

    latest_date = max(date_folders, key=lambda d: datetime.strptime(d, "%Y%m%d"))

    # S3 Key for latest data
    s3_key = f"{table_path}{latest_date}/{table_name}.parquet"
    print(f"Loading from: s3://{S3_BUCKET}/{s3_key}")

    # Read Parquet file from S3
    obj = s3_hook.get_key(s3_key, bucket_name=S3_BUCKET)
    buffer = BytesIO(obj.get()["Body"].read())
    df = pd.read_parquet(buffer, engine="pyarrow")

    # Connect to Redshift
    redshift_hook = RedshiftSQLHook(redshift_conn_id="redshift_ecommerce")
    conn = redshift_hook.get_conn()
    cursor = conn.cursor()

    # Upload DataFrame to Redshift
    for _, row in df.iterrows():
        values = []
        for value in row:
            if isinstance(value, pd.Timestamp):
                values.append("'{}'".format(value.strftime("%Y-%m-%d %H:%M:%S")))
            elif isinstance(value, str):
                values.append("'{}'".format(value.replace("'", "''")))
            else:
                values.append(str(value))

        values_str = ", ".join(values)
        sql = f"INSERT INTO {table_name} VALUES ({values_str})"
        print(sql)
        cursor.execute(sql)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Successfully loaded {table_name} into Redshift.")


# Default args
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 16),
    "catchup": False,
}

# Define DAG
dag = DAG(
    "data_pipeline",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
)

# Task to list tables
list_tables_task = PythonOperator(
    task_id="list_tables",
    python_callable=list_tables,
    dag=dag,
)

list_tables_redshift_task = PythonOperator(
    task_id="list_tables_redshift",
    python_callable=list_tables_redshift,
    dag=dag,
)

sync_task = EmptyOperator(
    task_id="sync_all_uploads",
    dag=dag,
)

# Generate dynamic tasks for each table
table_names = list_tables()
table_names_redshift = list_tables_redshift()

fetch_ddb_then_upload = PythonOperator(
    task_id="fetch_ddb_then_upload", python_callable=fetch_ddb_then_upload_, dag=dag
)

list_tables_redshift_task >> list_tables_task
list_tables_task >> fetch_ddb_then_upload >> sync_task

for table in table_names:
    task = PythonOperator(
        task_id=f"upload_{table}",
        python_callable=fetch_table_data_and_upload,
        op_kwargs={"table_name": table},
        dag=dag,
    )
    list_tables_task >> task >> sync_task

for table in table_names_redshift:
    to_olap_task = PythonOperator(
        task_id=f"load_gold_{table}_to_redshift",
        python_callable=load_gold_to_redshift,
        op_kwargs={"table_name": table},
        dag=dag,
    )
    sync_task >> to_olap_task
