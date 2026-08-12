import csv
import io
import os
import sqlite3

TABLE_NAME = "uploaded_data"
CUSTOMER_TABLE = "customers"

# 5 columns picked from StockTable
COLUMNS = ["item_code", "item_tag", "purity", "net_weight", "gross_weight"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # this = src/db

_db_path_cache = None


def get_db_path():
    """Resolve the DB path lazily (on first real use), not at import time.

    Flet 0.86+ exposes the durable, app-private data directory via the
    FLET_APP_STORAGE_DATA environment variable (there is no ft.app_data_path
    attribute in this version -- referencing it always raises AttributeError,
    on desktop and on-device alike). This directory is pre-created, preserved
    across app updates, and is also the process's working directory in
    production builds. We still resolve lazily and cache the result so it's
    read once the runtime has actually set the env var.
    """
    global _db_path_cache
    if _db_path_cache:
        return _db_path_cache

    storage_data_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if storage_data_dir:
        _db_path_cache = os.path.join(storage_data_dir, "data.db")
        print(f"DB_PATH IN USE (FLET_APP_STORAGE_DATA): {_db_path_cache}")
        return _db_path_cache

    _db_path_cache = os.path.abspath(os.path.join(BASE_DIR, "..", "data.db"))
    print(f"DB_PATH IN USE (fallback): {_db_path_cache}")
    return _db_path_cache


# ---------- stock ledger ----------

def store_csv_in_sqlite(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))

    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header row")

    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

    missing = [c for c in COLUMNS if c not in reader.fieldnames]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")

    rows = []
    for row in reader:
        rows.append(tuple(row.get(col, "") for col in COLUMNS))

    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    cur.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            item_code TEXT,
            item_tag TEXT,
            purity TEXT,
            net_weight REAL,
            gross_weight REAL
        )
    """)

    cur.executemany(
        f"INSERT INTO {TABLE_NAME} (item_code, item_tag, purity, net_weight, gross_weight) VALUES (?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()
    return COLUMNS, len(rows)


def fetch_preview(limit=50):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {TABLE_NAME} LIMIT ?", (limit,))
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


def search_stock(query, limit=50):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    like = f"%{query.strip()}%"
    try:
        cur.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE item_code LIKE ? OR item_tag LIKE ? LIMIT ?",
            (like, like, limit),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


def fetch_by_item_codes(item_codes):
    """Returns full stock rows for the given item_codes."""
    if not item_codes:
        return []
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in item_codes)
    try:
        cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE item_code IN ({placeholders})", item_codes)
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


# ---------- customers ----------

def init_customer_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {CUSTOMER_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            customer_number TEXT UNIQUE
        )
    """)
    # Add unique indexes for existing tables that lack them
    try:
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_code ON {CUSTOMER_TABLE} (customer_code)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_number ON {CUSTOMER_TABLE} (customer_number)")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def _check_customer_duplicates(conn, customer_code, customer_number, exclude_id=None):
    """Raise ValueError if customer_code or customer_number already exists."""
    exclude_clause = "AND id != ?" if exclude_id else ""
    params_code = [customer_code] + ([exclude_id] if exclude_id else [])
    params_number = [customer_number] + ([exclude_id] if exclude_id else [])

    row = conn.execute(
        f"SELECT id FROM {CUSTOMER_TABLE} WHERE customer_code = ? {exclude_clause}",
        params_code,
    ).fetchone()
    if row:
        raise ValueError(f"Customer Code '{customer_code}' already exists.")

    if customer_number:  # only check when a number is provided
        row = conn.execute(
            f"SELECT id FROM {CUSTOMER_TABLE} WHERE customer_number = ? {exclude_clause}",
            params_number,
        ).fetchone()
        if row:
            raise ValueError(f"Customer Number '{customer_number}' already exists.")


def store_customer(customer_code, customer_name, customer_number):
    init_customer_table()
    code = customer_code.strip()
    number = (customer_number or "").strip()
    conn = sqlite3.connect(get_db_path())
    try:
        _check_customer_duplicates(conn, code, number)
        conn.execute(
            f"INSERT INTO {CUSTOMER_TABLE} (customer_code, customer_name, customer_number) VALUES (?, ?, ?)",
            (code, customer_name.strip(), number),
        )
        conn.commit()
    finally:
        conn.close()


def update_customer(customer_id, customer_code, customer_name, customer_number):
    init_customer_table()
    code = customer_code.strip()
    number = (customer_number or "").strip()
    conn = sqlite3.connect(get_db_path())
    try:
        _check_customer_duplicates(conn, code, number, exclude_id=customer_id)
        conn.execute(
            f"""UPDATE {CUSTOMER_TABLE}
                SET customer_code = ?, customer_name = ?, customer_number = ?
                WHERE id = ?""",
            (code, customer_name.strip(), number, customer_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_customer(customer_id):
    """Delete a customer row by id."""
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"DELETE FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()


def fetch_customers(limit=100):
    """Returns rows as (id, customer_code, customer_name, customer_number)."""
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, customer_code, customer_name, customer_number FROM {CUSTOMER_TABLE} ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows