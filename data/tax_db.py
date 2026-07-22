"""
Tax Database — Corporate Tax Manager
SQLite comprehensive schema for corporate tax operations.
- Transaksi PPh 23/26, PPh Final, PPh 21
- Manajemen dokumen perpajakan
- Laporan agregat per periode
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple


def _default_db_path() -> str:
    """Resolve writable DB path for Android APK and desktop/Termux."""
    # Android private app storage (set by python-for-android)
    for key in ('ANDROID_PRIVATE', 'ANDROID_APP_PATH'):
        base = os.environ.get(key)
        if base:
            try:
                os.makedirs(base, exist_ok=True)
                return os.path.join(base, 'tax_data.db')
            except Exception:
                pass

    # Fallback: user home (writable on Android/Termux)
    try:
        home = os.path.expanduser('~')
        if home and home != '~' and os.path.isdir(home):
            data_dir = os.path.join(home, '.corporate_tax_manager')
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, 'tax_data.db')
    except Exception:
        pass

    # Last resort: project directory (desktop only)
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project, 'tax_data.db')


DB_PATH = _default_db_path()


class TaxDB:
    """Database layer untuk Corporate Tax Manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_db_path()

    def _conn(self) -> sqlite3.Connection:
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        return conn

    def init_tables(self):
        """Initialize all tables. Safe to call on every startup."""
        conn = self._conn()
        cursor = conn.cursor()

        tables = [
            """
            CREATE TABLE IF NOT EXISTS tax_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS withholding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL,
                obj_type TEXT NOT NULL,
                tax_code TEXT DEFAULT 'pph23',
                tariff_label TEXT DEFAULT '2%',
                pph_amount REAL NOT NULL DEFAULT 0,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                tax_year INTEGER NOT NULL DEFAULT (CAST(strftime('%Y', 'now') AS INTEGER)),
                tax_month INTEGER NOT NULL DEFAULT (CAST(strftime('%m', 'now') AS INTEGER))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Umum',
                status TEXT NOT NULL DEFAULT 'Lengkap',
                tax_year INTEGER,
                tax_month INTEGER,
                notes TEXT,
                file_path TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pph21_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                gross_salary REAL NOT NULL,
                dependents INTEGER DEFAULT 0,
                ptkp_status TEXT DEFAULT 'TK0',
                pph21_amount REAL NOT NULL,
                period_year INTEGER NOT NULL,
                period_month INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tax_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                deadline_date TEXT NOT NULL,
                tax_code TEXT,
                is_recurring INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """,
        ]

        for stmt in tables:
            cursor.execute(stmt)

        # Seed default tax reminders if empty
        cursor.execute("SELECT COUNT(*) FROM tax_reminders")
        if cursor.fetchone()[0] == 0:
            defaults = [
                ('SPT Masa PPN', 'Lapor dan bayar PPN masa', '10', 'ppn', 1),
                ('PPh 21 Masa', 'Penyetoran PPh 21 masa', '20', 'pph21', 1),
                ('PPh 23/26 Masa', 'Penyetoran PPh 23/26 masa', '20', 'pph23', 1),
                ('PPh Final Masa', 'Penyetoran PPh Final (pp 23/sewa)', '15', 'pph_final', 1),
                ('PPh 26 Masa', 'Penyetoran PPh 26 masa', '21', 'pph26', 1),
            ]
            cursor.executemany(
                "INSERT INTO tax_reminders (title, description, deadline_date, tax_code, is_recurring) VALUES (?,?,?,?,?)",
                defaults)

        conn.commit()
        conn.close()

    # ═══════════════════════════════════════════════════════
    # WITHHOLDING (PPh 23/26/4(2))
    # ═══════════════════════════════════════════════════════

    def add_withholding(self, vendor: str, amount: float, obj_type: str,
                        tax_code: str = 'pph23', tariff_label: str = '2%',
                        description: str = '') -> int:
        conn = self._conn()
        cursor = conn.cursor()
        now = datetime.now()

        tariff_map = {'2%': 0.02, '15%': 0.15, '20%': 0.20, '10%': 0.10, '0.5%': 0.005}
        tariff = tariff_map.get(tariff_label.strip(), 0.02)
        pph_amount = amount * tariff

        cursor.execute("""
            INSERT INTO withholding (vendor, amount, obj_type, tax_code, tariff_label, pph_amount, description,
                                     created_at, tax_year, tax_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)
        """, (vendor, amount, obj_type, tax_code, tariff_label, pph_amount, description,
              now.year, now.month))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_all_withholding(self, limit: int = 100, offset: int = 0,
                            year: Optional[int] = None,
                            month: Optional[int] = None,
                            tax_code: Optional[str] = None) -> Tuple[List[Dict], int]:
        conn = self._conn()
        cursor = conn.cursor()

        conditions = []
        params = []
        if year:
            conditions.append("tax_year = ?")
            params.append(year)
        if month:
            conditions.append("tax_month = ?")
            params.append(month)
        if tax_code:
            conditions.append("tax_code = ?")
            params.append(tax_code)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Total count
        cursor.execute(f"SELECT COUNT(*) FROM withholding {where}", params)
        total = cursor.fetchone()[0]

        # Data
        cursor.execute(f"""
            SELECT id, vendor, amount, obj_type, tax_code, tariff_label, pph_amount,
                   COALESCE(description,'') as description, created_at, tax_year, tax_month
            FROM withholding {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows, total

    def get_summary_by_period(self, year: int, month: int) -> Dict:
        """Get tax payment summary for a specific period."""
        conn = self._conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tax_code, obj_type, COUNT(*) as count, SUM(amount) as total_amount, SUM(pph_amount) as total_tax
            FROM withholding
            WHERE tax_year = ? AND tax_month = ?
            GROUP BY tax_code, obj_type
            ORDER BY tax_code
        """, (year, month))
        details = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0) FROM withholding
            WHERE tax_year = ? AND tax_month = ?
        """, (year, month))
        grand_total = cursor.fetchone()[0]

        conn.close()
        return {
            'year': year,
            'month': month,
            'grand_total': grand_total,
            'details': details,
            'count': len(details),
        }

    def get_yearly_summary(self, year: int) -> List[Dict]:
        """Monthly breakdown for a year."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tax_month, tax_code, COUNT(*) as count, SUM(amount) as total_amount, SUM(pph_amount) as total_tax
            FROM withholding
            WHERE tax_year = ?
            GROUP BY tax_month, tax_code
            ORDER BY tax_month, tax_code
        """, (year,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def delete_withholding(self, record_id: int) -> bool:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM withholding WHERE id = ?", (record_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ═══════════════════════════════════════════════════════
    # PPh 21 LOG
    # ═══════════════════════════════════════════════════════

    def add_pph21(self, employee_name: str, gross_salary: float,
                  dependents: int, ptkp_status: str,
                  pph21_amount: float, year: int, month: int) -> int:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pph21_log (employee_name, gross_salary, dependents, ptkp_status,
                                   pph21_amount, period_year, period_month)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_name, gross_salary, dependents, ptkp_status, pph21_amount, year, month))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_pph21_log(self, limit: int = 100) -> List[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, employee_name, gross_salary, dependents, ptkp_status,
                   pph21_amount, period_year, period_month, created_at
            FROM pph21_log
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_total_pph21(self, year: int) -> float:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(pph21_amount), 0)
            FROM pph21_log WHERE period_year = ?
        """, (year,))
        total = cursor.fetchone()[0]
        conn.close()
        return total

    # ═══════════════════════════════════════════════════════
    # DOCUMENTS
    # ═══════════════════════════════════════════════════════

    def add_document(self, title: str, category: str = 'Umum',
                     status: str = 'Lengkap', tax_year: Optional[int] = None,
                     tax_month: Optional[int] = None, notes: str = '',
                     file_path: str = '') -> int:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (title, category, status, tax_year, tax_month, notes, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, category, status, tax_year, tax_month, notes, file_path or None))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_all_documents(self, limit: int = 100, offset: int = 0,
                          category: Optional[str] = None,
                          status_filter: Optional[str] = None) -> Tuple[List[Dict], int]:
        conn = self._conn()
        cursor = conn.cursor()

        conditions = []
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor.execute(f"SELECT COUNT(*) FROM documents {where}", params)
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT id, title, category, status, tax_year, tax_month,
                   COALESCE(notes,'') as notes, created_at
            FROM documents {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows, total

    def delete_document(self, doc_id: int) -> bool:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ═══════════════════════════════════════════════════════
    # REMINDERS / DEADLINES
    # ═══════════════════════════════════════════════════════

    def get_upcoming_deadlines(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming tax deadlines within the specified days."""
        today = date.today()
        conn = self._conn()
        cursor = conn.cursor()

        # Get recurring reminders
        cursor.execute("""
            SELECT id, title, description, deadline_date, tax_code
            FROM tax_reminders
            WHERE is_active = 1 AND is_recurring = 1
            ORDER BY CAST(deadline_date AS INTEGER)
        """)
        reminders = [dict(r) for r in cursor.fetchall()]
        conn.close()

        deadlines = []
        today_ord = today.toordinal()

        for r in reminders:
            dl_day = int(r['deadline_date'])
            # Construct deadline date for this month
            for m_offset in range(3):  # this month, next month, month after
                y = today.year
                m = today.month + m_offset
                if m > 12:
                    m -= 12
                    y += 1
                try:
                    dl = date(y, m, dl_day)
                except ValueError:
                    continue

                diff = (dl - today).days
                if diff < -15:
                    continue  # Already way past
                if diff > days_ahead:
                    continue

                status = 'OK'
                if diff < 0:
                    status = 'LEWAT'
                elif diff <= 7:
                    status = 'SEGERA'

                deadlines.append({
                    'id': r['id'],
                    'title': r['title'],
                    'description': r.get('description', ''),
                    'date': dl.strftime('%d %b %Y'),
                    'date_ordinal': dl.toordinal(),
                    'days_left': diff,
                    'status': status,
                    'tax_code': r['tax_code'],
                })

        deadlines.sort(key=lambda x: abs(x['days_left']) if x['days_left'] < 0 else x['days_left'])
        return deadlines

    # ═══════════════════════════════════════════════════════
    # DASHBOARD AGGREGATION
    # ═══════════════════════════════════════════════════════

    def get_dashboard_data(self) -> Dict:
        """Aggregate data for main dashboard."""
        now = datetime.now()
        year, month = now.year, now.month

        conn = self._conn()
        cursor = conn.cursor()

        # Total PPh due this month
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0) FROM withholding
            WHERE tax_year = ? AND tax_month = ?
        """, (year, month))
        total_due = cursor.fetchone()[0]

        # Total PPh this year
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0) FROM withholding
            WHERE tax_year = ?
        """, (year,))
        total_year = cursor.fetchone()[0]

        # Document counts
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM documents GROUP BY status
        """)
        doc_by_status = {r['status']: r['cnt'] for r in cursor.fetchall()}

        # Count by tax type this month
        cursor.execute("""
            SELECT tax_code, COUNT(*) as cnt, COALESCE(SUM(pph_amount), 0) as total
            FROM withholding WHERE tax_year = ? AND tax_month = ?
            GROUP BY tax_code
        """, (year, month))
        by_type = [dict(r) for r in cursor.fetchall()]

        # Count by category
        cursor.execute("""
            SELECT category, COUNT(*) as cnt FROM documents GROUP BY category
        """)
        doc_by_category = [dict(r) for r in cursor.fetchall()]

        conn.close()

        return {
            'total_due_this_month': total_due,
            'total_year': total_year,
            'doc_count': doc_count,
            'doc_by_status': doc_by_status,
            'by_type': by_type,
            'doc_by_category': doc_by_category,
            'month': month,
            'year': year,
        }
