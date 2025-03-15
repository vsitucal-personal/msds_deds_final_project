from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime

def list_tables():
    hook = PostgresHook(postgres_conn_id="ecommerce")
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"Table: {table[0]}")
    cursor.close()
    conn.close()

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 3, 16),
    "catchup": False
}

dag = DAG(
    "ecommerce_show_tables",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False
)

show_tables_task = PythonOperator(
    task_id="show_tables",
    python_callable=list_tables,
    dag=dag
)

show_tables_task