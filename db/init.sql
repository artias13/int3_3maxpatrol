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

INSERT INTO scan_results (ip, os, version, architecture, detected_os, created_at) VALUES ('xyz123@gmail.com'), ('dasd@mail.ru');
INSERT INTO phone_numbers (phone_number) VALUES ('+7 123 123 33 45'), ('+8-534-555-66-33');