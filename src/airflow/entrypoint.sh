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

airflow connections add 'aws_default' \
    --conn-type 'aws' \
    --conn-extra '{"aws_access_key_id": "'$AWS_ACCESS_KEY_ID'", "aws_secret_access_key": "'$AWS_SECRET_ACCESS_KEY'"}'


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
