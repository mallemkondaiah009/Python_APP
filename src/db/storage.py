import csv
import io
import os
import sqlite3

import flet as ft

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

    # fallback: FLET_APP_STORAGE_DATA isn't set (e.g. running `python main.py`
    # directly instead of `flet run`/a packaged build) -- resolve relative to
    # src/, not wherever the process was launched from
    _db_path_cache = os.path.abspath(os.path.join(BASE_DIR, "..", "data.db"))
    print(f"DB_PATH IN USE (fallback): {_db_path_cache}")
    return _db_path_cache


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


def init_customer_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {CUSTOMER_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_number TEXT
        )
    """)
    conn.commit()
    conn.close()


def store_customer(customer_code, customer_name, customer_number):
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        f"INSERT INTO {CUSTOMER_TABLE} (customer_code, customer_name, customer_number) VALUES (?, ?, ?)",
        (customer_code.strip(), customer_name.strip(), (customer_number or "").strip()),
    )
    conn.commit()
    conn.close()


def update_customer(customer_id, customer_code, customer_name, customer_number):
    """Update an existing customer row by id."""
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        f"""UPDATE {CUSTOMER_TABLE}
            SET customer_code = ?, customer_name = ?, customer_number = ?
            WHERE id = ?""",
        (customer_code.strip(), customer_name.strip(), (customer_number or "").strip(), customer_id),
    )
    conn.commit()
    conn.close()


def delete_customer(customer_id):
    """Delete a customer row by id, and any stock links pointing to it."""
    init_customer_table()
    init_link_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"DELETE FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    conn.execute(f"DELETE FROM {LINK_TABLE} WHERE customer_id = ?", (customer_id,))
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


LINK_TABLE = "stock_customer_links"


def init_link_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {LINK_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT NOT NULL,
            customer_id INTEGER NOT NULL,
            UNIQUE(item_code, customer_id)
        )
    """)
    conn.commit()
    conn.close()


def link_customer_to_item(item_code, customer_id):
    init_link_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        f"INSERT OR IGNORE INTO {LINK_TABLE} (item_code, customer_id) VALUES (?, ?)",
        (item_code, customer_id),
    )
    conn.commit()
    conn.close()


def unlink_customer_from_item(item_code, customer_id):
    init_link_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        f"DELETE FROM {LINK_TABLE} WHERE item_code = ? AND customer_id = ?",
        (item_code, customer_id),
    )
    conn.commit()
    conn.close()


def get_linked_customers(item_code):
    """Returns [(customer_id, customer_code, customer_name), ...] linked to this item."""
    init_customer_table()
    init_link_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"""
        SELECT c.id, c.customer_code, c.customer_name
        FROM {LINK_TABLE} l
        JOIN {CUSTOMER_TABLE} c ON c.id = l.customer_id
        WHERE l.item_code = ?
        ORDER BY c.customer_name
    """, (item_code,))
    rows = cur.fetchall()
    conn.close()
    return rows


def export_ledger_csv():
    """Returns CSV text: stock columns + a linked_customers column (comma-joined names)."""
    init_link_table()
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT u.rowid, u.item_code, u.item_tag, u.purity, u.net_weight, u.gross_weight,
                   GROUP_CONCAT(c.customer_name, ', ') AS customers
            FROM {TABLE_NAME} u
            LEFT JOIN {LINK_TABLE} l ON l.item_code = u.item_code
            LEFT JOIN {CUSTOMER_TABLE} c ON c.id = l.customer_id
            GROUP BY u.rowid
            ORDER BY u.rowid
        """)
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(COLUMNS + ["linked_customers"])
    for row in rows:
        _, item_code, item_tag, purity, net_weight, gross_weight, customers = row
        writer.writerow([item_code, item_tag, purity, net_weight, gross_weight, customers or ""])
    return output.getvalue()