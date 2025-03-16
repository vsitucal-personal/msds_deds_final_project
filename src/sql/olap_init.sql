CREATE TABLE customer (
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    joined_at TIMESTAMP
);

CREATE TABLE category (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(100)
);

CREATE TABLE vendor (
    vendor_id INT PRIMARY KEY,
    vendor_name VARCHAR(100),
    region VARCHAR(100),
    joined_at TIMESTAMP
);

CREATE TABLE date (
    date_id INT PRIMARY KEY,
    year INT,
    month INT,
    day INT
);

CREATE TABLE inventory (
    item_id INT PRIMARY KEY,
    item_name VARCHAR(100),
    category INT,
    price DECIMAL(10,2),
    updated_at TIMESTAMP,
    vendor_id INT
);

CREATE TABLE sales (
    item_id INT,
    customer_id INT,
    vendor_id INT,
    category_id INT,
    date_id INT,
    unit_price DECIMAL(10,2),
    qty INT,
    total_price DECIMAL(10,2)
);