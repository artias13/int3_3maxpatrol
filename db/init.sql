
CREATE DATABASE ${DB_DATABASE};

\c db_bot;

CREATE TABLE system_info (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(50),
    os TEXT,
    architecture TEXT,
    uptime TEXT,
    disk_space TEXT,
    memory_usage TEXT,
    mpstat_data TEXT,
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
