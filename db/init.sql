CREATE DATABASE ${DB_DATABASE};

\c vm_scanner_db;

CREATE TABLE scan_results (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(255),
    os VARCHAR(100),
    version VARCHAR(50),
    architecture VARCHAR(50),
    detected_os VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);