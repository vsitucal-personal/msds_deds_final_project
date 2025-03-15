from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator

from airflow import DAG


def hello_world():
    print("Hello, Airflow!")


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2024, 3, 16),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "basic_dag",
    default_args=default_args,
    description="A simple Airflow DAG",
    schedule_interval=timedelta(days=1),
    catchup=False,
)

task_hello = PythonOperator(
    task_id="hello_task",
    python_callable=hello_world,
    dag=dag,
)

task_hello
