#!/bin/bash
# Initialize the database
airflow db init
airflow connections delete all
airflow connections add 'ecommerce' \
    --conn-type 'postgres' \
    --conn-host 'db' \
    --conn-schema 'ecommerce' \
    --conn-login $POSTGRES_USER \
    --conn-password $POSTGRES_PASSWORD \
    --conn-port 5432

airflow users create \
    --username $AF_USER \
    --password $AF_PASS \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
airflow webserver &
sleep 5
exec airflow scheduler
