"""Database ya Chakula-Smart (SQLite).

Inajumuisha: wauzaji (simu + PIN), matangazo, oda, na muhtasari wa muuzaji.
Prototype: PIN pekee haithibitishi umiliki wa namba ya simu (OTP bado).
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CHAKULA_DB", ROOT / "data" / "chakula_smart.db"))

PIN_ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


# ------------------------------------------------------------ connection
def get_connection():
    """Kwa msimbo wa zamani; tumia db() kwa code mpya."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db(write=False):
    """Connection salama: inafunga yenyewe, na kuandika ni transaction moja."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if write:
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        if write:
            conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _add_column_if_missing(conn, table, column, ddl):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def initialize_database():
    with db(write=True) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                area TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL,
                dish TEXT NOT NULL,
                portions INTEGER NOT NULL CHECK(portions >= 0),
                base_price INTEGER NOT NULL,
                current_price INTEGER NOT NULL,
                cost_price INTEGER NOT NULL,
                discount_pct REAL DEFAULT 0,
                area TEXT NOT NULL,
                image TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(vendor_id) REFERENCES vendors(id)
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_price INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY(listing_id) REFERENCES listings(id)
            )""")
        # migration: hazifuti data za zamani
        _add_column_if_missing(conn, "vendors", "pin_hash", "TEXT")
        _add_column_if_missing(conn, "vendors", "failed_attempts", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "vendors", "locked_until", "TEXT")


def ensure_vendor_pin_column():
    """Imebaki kwa ulinganifu; initialize_database() tayari inafanya migration."""
    initialize_database()


# ------------------------------------------------------------ phone & PIN
def normalize_phone(raw):
    """Badilisha namba iwe 2557XXXXXXXX. Inakubali 0712 345 678, +255712345678, 712345678."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("255"):
        pass
    elif len(digits) == 10 and digits.startswith("0"):
        digits = "255" + digits[1:]
    elif len(digits) == 9:
        digits = "255" + digits
    else:
        raise ValueError("Namba ya simu si sahihi. Mfano: 0712 345 678")
    if digits[3] not in "67":
        raise ValueError("Namba ya simu si sahihi. Mfano: 0712 345 678")
    return digits


def pretty_phone(normalized):
    return f"0{normalized[3:6]} {normalized[6:9]} {normalized[9:]}" if len(normalized) == 12 else normalized


def validate_pin(pin):
    if not pin or not pin.isdigit() or not 4 <= len(pin) <= 6:
        raise ValueError("PIN lazima iwe na tarakimu 4 hadi 6.")


def hash_vendor_pin(pin):
    validate_pin(pin)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), PIN_ITERATIONS).hex()
    return f"{salt}${digest}"


def _pin_matches(pin, stored):
    try:
        salt, digest = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False
    test = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), PIN_ITERATIONS).hex()
    return hmac.compare_digest(test, digest)


# ------------------------------------------------------------ vendors
def register_vendor_secure(name, phone, area, pin):
    name, area = (name or "").strip(), (area or "").strip()
    if len(name) < 2 or len(area) < 2:
        raise ValueError("Jaza jina na eneo kwa usahihi.")
    phone = normalize_phone(phone)
    pin_hash = hash_vendor_pin(pin)
    try:
        with db(write=True) as conn:
            cur = conn.execute(
                "INSERT INTO vendors (name, phone, area, created_at, pin_hash) VALUES (?,?,?,?,?)",
                (name, phone, area, datetime.now().isoformat(), pin_hash),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("Namba hii tayari imesajiliwa. Ingia kwenye akaunti yako.")


def get_vendor_by_phone(phone):
    phone = normalize_phone(phone)
    with db() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE phone = ?", (phone,)).fetchone()
        return dict(row) if row else None


def vendor_needs_pin(phone):
    """True kama akaunti ipo lakini haina PIN (akaunti za majaribio za zamani)."""
    v = get_vendor_by_phone(phone)
    return bool(v) and not v["pin_hash"]


def verify_vendor_login(phone, pin):
    """Rudisha vendor (dict) au itupe ValueError yenye ujumbe wa kuonyesha.
    Makosa 5 mfululizo yanafunga akaunti kwa dakika 15."""
    phone = normalize_phone(phone)
    validate_pin(pin)
    vendor, error = None, "Namba au PIN si sahihi."
    with db(write=True) as conn:
        v = conn.execute("SELECT * FROM vendors WHERE phone = ?", (phone,)).fetchone()
        if v is None or not v["pin_hash"]:
            _pin_matches(pin, "00$00")  # muda sawa, ili usijue kama akaunti ipo
        elif v["locked_until"] and datetime.fromisoformat(v["locked_until"]) > datetime.now():
            left = datetime.fromisoformat(v["locked_until"]) - datetime.now()
            error = f"Akaunti imefungwa kwa muda. Jaribu tena baada ya dakika {int(left.total_seconds() // 60) + 1}."
        elif _pin_matches(pin, v["pin_hash"]):
            conn.execute("UPDATE vendors SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (v["id"],))
            vendor = dict(v)
        else:
            attempts = v["failed_attempts"] + 1
            if attempts >= MAX_FAILED_ATTEMPTS:
                until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).isoformat()
                conn.execute("UPDATE vendors SET failed_attempts = 0, locked_until = ? WHERE id = ?", (until, v["id"]))
            else:
                conn.execute("UPDATE vendors SET failed_attempts = ? WHERE id = ?", (attempts, v["id"]))
    if vendor is None:
        raise ValueError(error)
    return vendor


def set_legacy_vendor_pin(phone, pin):
    """PROTOTYPE TU: weka PIN ya kwanza kwa akaunti ya zamani isiyo na PIN.
    Production: lazima OTP kwanza, vinginevyo mtu yeyote anaweza kuchukua akaunti."""
    phone = normalize_phone(phone)
    pin_hash = hash_vendor_pin(pin)
    with db(write=True) as conn:
        v = conn.execute("SELECT id, pin_hash FROM vendors WHERE phone = ?", (phone,)).fetchone()
        if v is None or v["pin_hash"]:
            raise ValueError("Akaunti haiwezi kuwekewa PIN kwa njia hii.")
        conn.execute("UPDATE vendors SET pin_hash = ? WHERE id = ?", (pin_hash, v["id"]))
        return dict(conn.execute("SELECT * FROM vendors WHERE id = ?", (v["id"],)).fetchone())


# ------------------------------------------------------------ listings
def publish_listing(vendor_id, dish, portions, base_price, current_price,
                    cost_price, discount_pct, area, image=None):
    with db(write=True) as conn:
        cur = conn.execute("""
            INSERT INTO listings (vendor_id, dish, portions, base_price, current_price,
                                  cost_price, discount_pct, area, image, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (vendor_id, dish, portions, base_price, current_price, cost_price,
             discount_pct, area, image, datetime.now().isoformat()))
        return cur.lastrowid


def get_active_listings(area=None):
    sql = """SELECT listings.*, vendors.name AS vendor_name, vendors.phone AS vendor_phone
             FROM listings JOIN vendors ON vendors.id = listings.vendor_id
             WHERE listings.status = 'active' AND listings.portions > 0"""
    args = ()
    if area:
        sql += " AND listings.area = ?"
        args = (area,)
    sql += " ORDER BY listings.created_at DESC"
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_vendor_listings(vendor_id):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM listings WHERE vendor_id = ? ORDER BY created_at DESC", (vendor_id,)).fetchall()
        return [dict(r) for r in rows]


def close_listing(listing_id, vendor_id):
    """Muuzaji anafunga ofa (mfano chakula kimeisha au anaondoka)."""
    with db(write=True) as conn:
        cur = conn.execute(
            "UPDATE listings SET status = 'closed' WHERE id = ? AND vendor_id = ? AND status = 'active'",
            (listing_id, vendor_id))
        if cur.rowcount == 0:
            raise ValueError("Ofa hii haiwezi kufungwa.")
        return True


# ------------------------------------------------------------ orders
def reserve_order(listing_id, customer_name, customer_phone, quantity):
    if quantity <= 0:
        raise ValueError("Idadi ya sahani lazima iwe zaidi ya sifuri.")
    with db(write=True) as conn:
        listing = conn.execute(
            "SELECT * FROM listings WHERE id = ? AND status = 'active'", (listing_id,)).fetchone()
        if listing is None:
            raise ValueError("Chakula hiki hakipatikani tena.")
        if listing["portions"] < quantity:
            raise ValueError("Sahani zilizobaki hazitoshi.")
        total = listing["current_price"] * quantity
        conn.execute("""UPDATE listings SET portions = portions - ?,
                        status = CASE WHEN portions - ? = 0 THEN 'sold_out' ELSE status END
                        WHERE id = ?""", (quantity, quantity, listing_id))
        cur = conn.execute("""INSERT INTO orders (listing_id, customer_name, customer_phone,
                              quantity, total_price, created_at) VALUES (?,?,?,?,?,?)""",
                           (listing_id, customer_name, customer_phone, quantity, total,
                            datetime.now().isoformat()))
        vendor = conn.execute(
            "SELECT name, phone FROM vendors WHERE id = ?", (listing["vendor_id"],)).fetchone()
        return {
            "order_id": cur.lastrowid,
            "total_price": total,
            "quantity": quantity,
            "dish": listing["dish"],
            "vendor_name": vendor["name"] if vendor else "",
            "vendor_phone": vendor["phone"] if vendor else "",
        }


def get_vendor_orders(vendor_id):
    with db() as conn:
        rows = conn.execute("""
            SELECT orders.id, orders.listing_id, orders.customer_name, orders.customer_phone,
                   orders.quantity, orders.total_price, orders.status, orders.created_at,
                   listings.dish, listings.area
            FROM orders JOIN listings ON listings.id = orders.listing_id
            WHERE listings.vendor_id = ? ORDER BY orders.created_at DESC""", (vendor_id,)).fetchall()
        return [dict(r) for r in rows]


def update_order_status(order_id, vendor_id, new_status):
    """Thibitisha au ghairi oda. Ikighairiwa, sahani zinarudi kwenye ofa."""
    if new_status not in ("confirmed", "cancelled"):
        raise ValueError("Hali ya oda hairuhusiwi.")
    with db(write=True) as conn:
        order = conn.execute("""
            SELECT orders.id, orders.listing_id, orders.quantity, orders.status
            FROM orders JOIN listings ON listings.id = orders.listing_id
            WHERE orders.id = ? AND listings.vendor_id = ?""", (order_id, vendor_id)).fetchone()
        if order is None:
            raise ValueError("Oda haijapatikana.")
        if order["status"] != "pending":
            raise ValueError("Oda hii tayari imeshughulikiwa.")
        if new_status == "cancelled":
            # ofa iliyofungwa na muuzaji haifunguliwi tena kwa bahati mbaya
            conn.execute("""UPDATE listings SET portions = portions + ?,
                            status = CASE WHEN status = 'sold_out' THEN 'active' ELSE status END
                            WHERE id = ?""", (order["quantity"], order["listing_id"]))
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        return True


def get_vendor_summary(vendor_id):
    with db() as conn:
        r = conn.execute("""
            SELECT
              (SELECT COUNT(*) FROM listings WHERE vendor_id = ? AND status = 'active') AS active_listings,
              COUNT(orders.id) AS orders_total,
              COALESCE(SUM(orders.status = 'pending'), 0) AS pending,
              COALESCE(SUM(orders.status = 'confirmed'), 0) AS confirmed,
              COALESCE(SUM(CASE WHEN orders.status = 'confirmed' THEN orders.total_price END), 0) AS revenue,
              COALESCE(SUM(CASE WHEN orders.status = 'confirmed' THEN orders.quantity END), 0) AS portions_sold
            FROM orders JOIN listings ON listings.id = orders.listing_id
            WHERE listings.vendor_id = ?""", (vendor_id, vendor_id)).fetchone()
        return dict(r)