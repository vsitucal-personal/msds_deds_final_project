CREATE TABLE IF NOT EXISTS customer (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    joined_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor (
    id SERIAL PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    region TEXT NOT NULL,
    joined_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INT NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    vendor_id INT REFERENCES vendor(id) ON DELETE CASCADE
);
