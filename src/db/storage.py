import csv
import io
import os
import sqlite3

TABLE_NAME = "uploaded_data"
CUSTOMER_TABLE = "customers"
ASSIGNMENTS_TABLE = "customer_assignments"

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
    """Delete a customer row by id and clean up assignments."""
    init_customer_table()
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"SELECT customer_name FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    row = cur.fetchone()
    cust_name = row[0] if row else None

    conn.execute(f"DELETE FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    if cust_name:
        conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE customer_name = ?", (cust_name,))
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


# ---------- customer assignments ----------

def init_assignments_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {ASSIGNMENTS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_code TEXT,
            item_code TEXT NOT NULL,
            item_tag TEXT,
            purity TEXT,
            net_weight REAL,
            gross_weight REAL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_name, item_code)
        )
    """)
    # Migration check for existing table missing columns
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({ASSIGNMENTS_TABLE})")
    existing_cols = {row[1] for row in cursor.fetchall()}

    expected_cols = {
        "customer_name": "TEXT",
        "customer_code": "TEXT",
        "item_tag": "TEXT",
        "purity": "TEXT",
        "net_weight": "REAL",
        "gross_weight": "REAL",
    }
    for col, col_type in expected_cols.items():
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE {ASSIGNMENTS_TABLE} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

    try:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_assignments_cust_name ON {ASSIGNMENTS_TABLE} (customer_name)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_assignments_item ON {ASSIGNMENTS_TABLE} (item_code)")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def save_customer_assignments(customer_id, item_codes):
    """Save customer assignments for given item_codes into DB table using customer_name and total stock row data."""
    init_assignments_table()
    if not item_codes:
        return
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    # 1. Fetch customer name & customer code
    cur.execute(f"SELECT customer_name, customer_code FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    cust_row = cur.fetchone()
    if not cust_row:
        conn.close()
        return
    cust_name, cust_code = cust_row[0], (cust_row[1] or "")

    # 2. Fetch full stock rows from uploaded_data
    placeholders = ",".join("?" for _ in item_codes)
    try:
        cur.execute(
            f"SELECT item_code, item_tag, purity, net_weight, gross_weight FROM {TABLE_NAME} WHERE item_code IN ({placeholders})",
            item_codes,
        )
        stock_rows = cur.fetchall()
    except sqlite3.OperationalError:
        stock_rows = []

    stock_dict = {row[0]: row[1:] for row in stock_rows}

    records = []
    for code in item_codes:
        stock_info = stock_dict.get(code, ("", "", 0.0, 0.0))
        tag, purity, net_w, gross_w = stock_info
        records.append((cust_name, cust_code, code, tag, purity, net_w, gross_w))

    cur.executemany(
        f"""INSERT OR REPLACE INTO {ASSIGNMENTS_TABLE} 
            (customer_name, customer_code, item_code, item_tag, purity, net_weight, gross_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
        records,
    )
    conn.commit()
    conn.close()


def update_item_assignments(item_code, customer_ids):
    """Replace all customer links for a given item_code in DB table using customer_name and total stock row data."""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE item_code = ?", (item_code,))
    if customer_ids:
        try:
            cur.execute(
                f"SELECT item_tag, purity, net_weight, gross_weight FROM {TABLE_NAME} WHERE item_code = ?",
                (item_code,),
            )
            s_row = cur.fetchone()
        except sqlite3.OperationalError:
            s_row = None

        tag, purity, net_w, gross_w = s_row if s_row else ("", "", 0.0, 0.0)

        cust_placeholders = ",".join("?" for _ in customer_ids)
        try:
            cur.execute(
                f"SELECT id, customer_name, customer_code FROM {CUSTOMER_TABLE} WHERE id IN ({cust_placeholders})",
                list(customer_ids),
            )
            cust_rows = cur.fetchall()
        except sqlite3.OperationalError:
            cust_rows = []

        records = []
        for cid, cname, ccode in cust_rows:
            records.append((cname, ccode or "", item_code, tag, purity, net_w, gross_w))

        cur.executemany(
            f"""INSERT OR REPLACE INTO {ASSIGNMENTS_TABLE}
                (customer_name, customer_code, item_code, item_tag, purity, net_weight, gross_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            records,
        )
    conn.commit()
    conn.close()


def fetch_assignments():
    """Returns stored assignments as dict mapping item_code -> set(customer_id)."""
    init_assignments_table()
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT a.item_code, c.id 
                FROM {ASSIGNMENTS_TABLE} a
                JOIN {CUSTOMER_TABLE} c ON a.customer_name = c.customer_name"""
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    result = {}
    for item_code, customer_id in rows:
        result.setdefault(item_code, set()).add(customer_id)
    return result


def clear_assignments():
    """Clear all stored customer assignments from DB table."""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE}")
    conn.commit()
    conn.close()

