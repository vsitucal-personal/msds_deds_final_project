from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow import DAG

# Replace with your S3 bucket name
S3_BUCKET = "mercado-ecommerce"
RAW_PREFIX = "raw/"
CLEAN_PREFIX = "clean/"
WORK_PREFIX = "work/"
GOLD_PREFIX = "gold/"


def list_tables():
    tables = ["customer", "vendor", "inventory"]
    return tables


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
        s3_key = f"{prefix}{today_str}/{table_name}.{file_format}"
        upload_func(data, key=s3_key, bucket_name=S3_BUCKET, replace=True)
        print(f"Uploaded {table_name}.{file_format} to s3://{S3_BUCKET}/{s3_key}")

    # Close DB connection
    cursor.close()
    conn.close()


# Default args
default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 16),
    "catchup": False,
}

# Define DAG
dag = DAG(
    "oltp_to_s3",
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

# Generate dynamic tasks for each table
table_names = list_tables()

for table in table_names:
    task = PythonOperator(
        task_id=f"upload_{table}",
        python_callable=fetch_table_data_and_upload,
        op_kwargs={"table_name": table},
        dag=dag,
    )
    list_tables_task >> task  # Set dependencies
