import csv
import io
import os
import sqlite3

import csv
import io
import os
import re
import sqlite3

TABLE_NAME = "stock"
CUSTOMER_TABLE = "customers"
ASSIGNMENTS_TABLE = "customer_assignments"

# 5 columns picked from StockTable
COLUMNS = ["item_no", "tag", "purity", "net_weight", "gross_weight"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # this = src/db

_db_path_cache = None


def get_db_path():
    """Resolve the DB path lazily (on first real use), not at import time."""
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

def _normalize_header(h):
    if not h:
        return ""
    clean = h.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "itemno": "item_no",
        "item_number": "item_no",
        "item": "item_no",
        "net_wt": "net_weight",
        "net_wt_(g)": "net_weight",
        "net_weight_(g)": "net_weight",
        "gross_wt": "gross_weight",
        "gross_wt_(g)": "gross_weight",
        "gross_weight_(g)": "gross_weight",
    }
    return aliases.get(clean, clean)


def _safe_float(val):
    if val is None:
        return 0.0
    s = str(val).strip().replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def store_csv_in_sqlite(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))

    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header row")

    # Map raw headers to normalized standard column names
    header_map = {}
    for raw in reader.fieldnames:
        if raw:
            norm = _normalize_header(raw)
            header_map[norm] = raw

    missing = [c for c in COLUMNS if c not in header_map]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")

    rows = []
    for row in reader:
        ino = str(row.get(header_map["item_no"], "") or "").strip()
        tag = str(row.get(header_map["tag"], "") or "").strip()
        purity = str(row.get(header_map["purity"], "") or "").strip()
        net_w = _safe_float(row.get(header_map["net_weight"]))
        gross_w = _safe_float(row.get(header_map["gross_weight"]))
        rows.append((ino, tag, purity, net_w, gross_w))

    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    cur.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            item_no TEXT,
            tag TEXT,
            purity TEXT,
            net_weight REAL,
            gross_weight REAL
        )
    """)

    cur.executemany(
        f"INSERT INTO {TABLE_NAME} (item_no, tag, purity, net_weight, gross_weight) VALUES (?, ?, ?, ?, ?)",
        rows,
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
            f"SELECT * FROM {TABLE_NAME} WHERE item_no LIKE ? OR tag LIKE ? OR (item_no || '-' || tag) LIKE ? LIMIT ?",
            (like, like, like, limit),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


def parse_item_query(q):
    """Parse composite queries like RG-101, rg-101, RG 101, rg101 into (item_no, tag)."""
    q_str = str(q).strip()
    m = re.match(r"^([A-Za-z]+)[-_\s]*(\d+.*)$", q_str)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    if "-" in q_str:
        parts = q_str.split("-", 1)
        return parts[0].strip().upper(), parts[1].strip().upper()
    if " " in q_str:
        parts = q_str.split(None, 1)
        return parts[0].strip().upper(), parts[1].strip().upper()
    if "_" in q_str:
        parts = q_str.split("_", 1)
        return parts[0].strip().upper(), parts[1].strip().upper()
    return q_str.upper(), q_str.upper()


def fetch_by_item_codes(queries):
    """Returns full stock rows for the given composite item queries (case-insensitive)."""
    if not queries:
        return []
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    found_rows = []
    seen_keys = set()

    for q in queries:
        raw = str(q).strip()
        if not raw:
            continue
        clean_upper = raw.upper()
        alphanumeric = re.sub(r'[^A-Z0-9]', '', clean_upper)

        parts = re.split(r'[-_\s]+', clean_upper)
        p1 = parts[0] if len(parts) > 0 else clean_upper
        p2 = parts[1] if len(parts) > 1 else ''

        m = re.match(r'^([A-Z]+)(\d+.*)$', clean_upper)
        m_p1 = m.group(1) if m else ''
        m_p2 = m.group(2) if m else ''

        try:
            cur.execute(
                f"""SELECT item_no, tag, purity, net_weight, gross_weight 
                    FROM {TABLE_NAME} 
                    WHERE UPPER(TRIM(item_no)) = ?
                       OR UPPER(TRIM(tag)) = ?
                       OR UPPER(TRIM(item_no) || '-' || TRIM(tag)) = ?
                       OR UPPER(TRIM(item_no) || ' ' || TRIM(tag)) = ?
                       OR UPPER(TRIM(item_no) || '_' || TRIM(tag)) = ?
                       OR UPPER(TRIM(item_no) || TRIM(tag)) = ?
                       OR (UPPER(TRIM(item_no)) = ? AND UPPER(TRIM(tag)) = ?)
                       OR (UPPER(TRIM(item_no)) = ? AND UPPER(TRIM(tag)) = ?)
                       OR (UPPER(TRIM(tag)) = ? AND UPPER(TRIM(item_no)) = ?)
                       OR REPLACE(REPLACE(REPLACE(UPPER(item_no || tag), '-', ''), '_', ''), ' ', '') = ?
                       OR (TRIM(tag) = '' AND UPPER(TRIM(item_no)) = ?)
                       OR (TRIM(tag) != '' AND (UPPER(TRIM(item_no)) = ? OR UPPER(TRIM(item_no || '-' || tag)) = ?))""",
                (
                    clean_upper, clean_upper, clean_upper, clean_upper, clean_upper, clean_upper,
                    p1, p2,
                    m_p1, m_p2,
                    p1, p2,
                    alphanumeric,
                    clean_upper,
                    clean_upper, clean_upper,
                ),
            )
            rows = cur.fetchall()
            for r in rows:
                key = f"{r[0]}-{r[1]}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    found_rows.append(r)
        except sqlite3.OperationalError:
            pass

    conn.close()
    return found_rows


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
    init_assignments_table()
    code = customer_code.strip()
    new_name = customer_name.strip()
    number = (customer_number or "").strip()
    conn = sqlite3.connect(get_db_path())
    try:
        _check_customer_duplicates(conn, code, number, exclude_id=customer_id)
        cur = conn.cursor()
        cur.execute(f"SELECT customer_name FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
        old_row = cur.fetchone()
        old_name = old_row[0] if old_row else None

        conn.execute(
            f"""UPDATE {CUSTOMER_TABLE}
                SET customer_code = ?, customer_name = ?, customer_number = ?
                WHERE id = ?""",
            (code, new_name, number, customer_id),
        )

        if old_name and old_name != new_name:
            conn.execute(
                f"UPDATE {ASSIGNMENTS_TABLE} SET customer_name = ?, customer_code = ? WHERE customer_name = ?",
                (new_name, code, old_name),
            )
        conn.commit()
    finally:
        conn.close()


def delete_customer(customer_id):
    """Delete a customer row by id and clean up all related assignment records."""
    init_customer_table()
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"SELECT customer_name, customer_code FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    row = cur.fetchone()
    cust_name = row[0] if row else None
    cust_code = row[1] if row else None

    conn.execute(f"DELETE FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))

    if cust_name:
        conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE customer_name = ?", (cust_name,))
    if cust_code:
        conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE customer_code = ?", (cust_code,))

    # Migration/legacy check for customer_id column if present
    cur.execute(f"PRAGMA table_info({ASSIGNMENTS_TABLE})")
    cols = {r[1] for r in cur.fetchall()}
    if "customer_id" in cols:
        conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE customer_id = ?", (customer_id,))

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
            item_no TEXT NOT NULL,
            tag TEXT NOT NULL,
            purity TEXT,
            net_weight REAL,
            gross_weight REAL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_name, item_no, tag)
        )
    """)
    # Migration check for existing table missing columns
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({ASSIGNMENTS_TABLE})")
    existing_cols = {row[1] for row in cursor.fetchall()}

    expected_cols = {
        "customer_name": "TEXT",
        "customer_code": "TEXT",
        "item_no": "TEXT",
        "tag": "TEXT",
        "purity": "TEXT",
        "net_weight": "REAL",
        "gross_weight": "REAL",
        "assigned_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
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
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_assignments_item_tag ON {ASSIGNMENTS_TABLE} (item_no, tag)")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def save_customer_assignments(customer_id, stock_rows):
    """Save customer assignments for given stock_rows into DB table."""
    init_assignments_table()
    if not stock_rows:
        return
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    cur.execute(f"SELECT customer_name, customer_code FROM {CUSTOMER_TABLE} WHERE id = ?", (customer_id,))
    cust_row = cur.fetchone()
    if not cust_row:
        conn.close()
        return
    cust_name, cust_code = cust_row[0], (cust_row[1] or "")

    records = []
    for r in stock_rows:
        ino, tag, purity, net_w, gross_w = r[0], r[1], r[2], r[3], r[4]
        records.append((cust_name, cust_code, ino, tag, purity, net_w, gross_w))

    cur.executemany(
        f"""INSERT OR REPLACE INTO {ASSIGNMENTS_TABLE} 
            (customer_name, customer_code, item_no, tag, purity, net_weight, gross_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
        records,
    )
    conn.commit()
    conn.close()


def update_item_assignments(item_no, tag, customer_ids):
    """Replace all customer links for a given (item_no, tag) in DB table."""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {ASSIGNMENTS_TABLE} WHERE item_no = ? AND tag = ?", (item_no, tag))
    if customer_ids:
        try:
            cur.execute(
                f"SELECT purity, net_weight, gross_weight FROM {TABLE_NAME} WHERE item_no = ? AND tag = ?",
                (item_no, tag),
            )
            s_row = cur.fetchone()
        except sqlite3.OperationalError:
            s_row = None

        purity, net_w, gross_w = s_row if s_row else ("", 0.0, 0.0)

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
            records.append((cname, ccode or "", item_no, tag, purity, net_w, gross_w))

        cur.executemany(
            f"""INSERT OR REPLACE INTO {ASSIGNMENTS_TABLE}
                (customer_name, customer_code, item_no, tag, purity, net_weight, gross_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            records,
        )
    conn.commit()
    conn.close()


def fetch_assignments():
    """Returns stored assignments as dict mapping 'item_no-tag' -> set(customer_id)."""
    init_assignments_table()
    init_customer_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT a.item_no, a.tag, c.id 
                FROM {ASSIGNMENTS_TABLE} a
                JOIN {CUSTOMER_TABLE} c ON a.customer_name = c.customer_name"""
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    result = {}
    for item_no, tag, customer_id in rows:
        key = f"{item_no}-{tag}"
        result.setdefault(key, set()).add(customer_id)
    return result


def clear_assignments():
    """Clear all stored customer assignments from DB table."""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    conn.execute(f"DELETE FROM {ASSIGNMENTS_TABLE}")
    conn.commit()
    conn.close()


def fetch_customer_totals_summary():
    """Returns customer totals as a list of dicts:
    [{'customer_name': ..., 'customer_code': ..., 'item_count': ..., 'total_net_weight': ..., 'total_gross_weight': ...}]
    """
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT customer_name, customer_code, 
                       COUNT(*) as item_count, 
                       COALESCE(SUM(CAST(net_weight AS REAL)), 0) as total_net, 
                       COALESCE(SUM(CAST(gross_weight AS REAL)), 0) as total_gross
                FROM {ASSIGNMENTS_TABLE}
                GROUP BY customer_name, customer_code
                ORDER BY customer_name ASC"""
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()

    result = []
    for r in rows:
        result.append({
            "customer_name": r[0],
            "customer_code": r[1] or "",
            "item_count": r[2],
            "total_net_weight": round(float(r[3]), 3),
            "total_gross_weight": round(float(r[4]), 3),
        })
    return result


def fetch_customer_purity_breakdown():
    """Returns purity breakdown as dict: { customer_name: { purity: total_net_weight } }"""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT customer_name, COALESCE(purity, 'Other') as purity_name, 
                       COALESCE(SUM(CAST(net_weight AS REAL)), 0) as total_net
                FROM {ASSIGNMENTS_TABLE}
                GROUP BY customer_name, purity_name"""
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()

    result = {}
    for cname, purity, total_net in rows:
        result.setdefault(cname, {})[purity] = round(float(total_net), 3)
    return result


def fetch_report_purities():
    """Returns sorted list of distinct purity values present in customer assignments."""
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT purity FROM {ASSIGNMENTS_TABLE} WHERE purity IS NOT NULL AND purity != '' ORDER BY purity ASC"
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [r[0] for r in rows if r[0]]


def fetch_report_assignments(customer_name=None, start_date=None, end_date=None, purity=None, search_query=None):
    """Fetch assigned items with flexible filtering criteria.
    Returns list of dicts with formatted values.
    """
    init_assignments_table()
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    conditions = []
    params = []

    if customer_name and str(customer_name).strip() and str(customer_name).strip().upper() != "ALL":
        conditions.append("LOWER(customer_name) = LOWER(?)")
        params.append(str(customer_name).strip())

    if purity and str(purity).strip() and str(purity).strip().upper() != "ALL":
        conditions.append("LOWER(purity) = LOWER(?)")
        params.append(str(purity).strip())

    if start_date and str(start_date).strip():
        s_date = str(start_date).strip()
        if len(s_date) == 10:
            s_date += " 00:00:00"
        conditions.append("assigned_at >= ?")
        params.append(s_date)

    if end_date and str(end_date).strip():
        e_date = str(end_date).strip()
        if len(e_date) == 10:
            e_date += " 23:59:59"
        conditions.append("assigned_at <= ?")
        params.append(e_date)

    if search_query and str(search_query).strip():
        q = f"%{str(search_query).strip().lower()}%"
        conditions.append(
            "(LOWER(item_no) LIKE ? OR LOWER(tag) LIKE ? OR LOWER(item_no || '-' || tag) LIKE ? OR LOWER(item_no || tag) LIKE ? OR LOWER(customer_name) LIKE ? OR LOWER(customer_code) LIKE ?)"
        )
        params.extend([q, q, q, q, q, q])

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    try:
        cur.execute(
            f"""SELECT id, customer_name, customer_code, item_no, tag, purity, 
                       net_weight, gross_weight, assigned_at
                FROM {ASSIGNMENTS_TABLE}
                {where_clause}
                ORDER BY assigned_at DESC, id DESC""",
            params,
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "customer_name": r[1] or "—",
            "customer_code": r[2] or "—",
            "item_no": r[3] or "",
            "tag": r[4] or "",
            "purity": r[5] or "—",
            "net_weight": round(float(r[6] or 0.0), 3),
            "gross_weight": round(float(r[7] or 0.0), 3),
            "assigned_at": str(r[8])[:19] if r[8] else "—",
        })
    return results




