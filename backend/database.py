import sqlite3

DATABASE = "phone_recovery.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_model TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            registered_at TEXT NOT NULL,
            last_seen TEXT,
            credential_hash TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS device_locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            accuracy REAL,
            reported_at TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            owner_id TEXT PRIMARY KEY,
            recovery_id TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS owner_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
        )
    """)


    columns = connection.execute(
        "PRAGMA table_info(devices)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "credential_hash" not in column_names:
        connection.execute(
            "ALTER TABLE devices ADD COLUMN credential_hash TEXT"
        )

    connection.commit()
    connection.close()
