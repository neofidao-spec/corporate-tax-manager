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
                remittance_status TEXT NOT NULL DEFAULT 'tercatat',
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
                remittance_status TEXT NOT NULL DEFAULT 'tercatat',
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

        # Lightweight migrations for remittance status (safe on existing DBs)
        for table in ('withholding', 'pph21_log'):
            cursor.execute(f'PRAGMA table_info({table})')
            cols = {row[1] for row in cursor.fetchall()}
            if 'remittance_status' not in cols:
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN remittance_status "
                    f"TEXT NOT NULL DEFAULT 'tercatat'"
                )

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
        vendor = (vendor or '').strip()
        if not vendor:
            raise ValueError('Nama vendor harus diisi')
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError('Jumlah bruto harus berupa angka')
        if amount < 0:
            raise ValueError('Jumlah bruto tidak boleh negatif')

        conn = self._conn()
        cursor = conn.cursor()
        now = datetime.now()

        tax_code = (tax_code or 'pph23').strip().lower()
        tariff_label = (tariff_label or '2%').strip()
        obj_type = (obj_type or 'Jasa').strip() or 'Jasa'

        # Prefer calculator rates when available so DB and UI stay consistent
        try:
            from data.tax_calculator import TaxCalculator
            calc = TaxCalculator()
            if tax_code == 'pph26':
                calc_res = calc.pph26(amount, obj_type)
            elif tax_code in ('pph_final', 'pph4_2', 'final'):
                # Final uses explicit tariff label
                calc_res = None
            else:
                calc_res = calc.pph23(amount, obj_type)
        except Exception:
            calc_res = None

        if calc_res is not None:
            pph_amount = float(calc_res['pph'])
            tariff_label = str(calc_res.get('tarif', tariff_label))
            obj_type = str(calc_res.get('jenis', obj_type))
        else:
            tariff_map = {
                '2%': 0.02, '15%': 0.15, '20%': 0.20, '10%': 0.10,
                '0.5%': 0.005, '2.5%': 0.025, '7.5%': 0.075, '4%': 0.04, '3%': 0.03,
            }
            tariff = tariff_map.get(tariff_label, 0.02)
            pph_amount = amount * tariff

        cursor.execute("""
            INSERT INTO withholding (vendor, amount, obj_type, tax_code, tariff_label, pph_amount, description,
                                     created_at, tax_year, tax_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)
        """, (vendor, amount, obj_type, tax_code, tariff_label, pph_amount, description or '',
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
                   COALESCE(description,'') as description,
                   COALESCE(remittance_status, 'tercatat') as remittance_status,
                   created_at, tax_year, tax_month
            FROM withholding {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows, total

    def get_summary_by_period(self, year: int, month: int) -> Dict:
        """Get tax payment summary for a specific period (withholding + PPh 21)."""
        try:
            year = int(year)
            month = int(month)
        except (TypeError, ValueError):
            raise ValueError('Tahun/bulan harus angka')
        if month < 1 or month > 12:
            raise ValueError('Bulan harus 1-12')

        conn = self._conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tax_code, obj_type, COUNT(*) as count,
                   COALESCE(SUM(amount), 0) as total_amount,
                   COALESCE(SUM(pph_amount), 0) as total_tax
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
        withholding_total = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COUNT(*) as count,
                   COALESCE(SUM(gross_salary), 0) as total_gross,
                   COALESCE(SUM(pph21_amount), 0) as total_tax
            FROM pph21_log
            WHERE period_year = ? AND period_month = ?
        """, (year, month))
        pph21_row = dict(cursor.fetchone())
        pph21_total = float(pph21_row.get('total_tax') or 0)
        pph21_count = int(pph21_row.get('count') or 0)
        pph21_gross = float(pph21_row.get('total_gross') or 0)

        if pph21_count > 0:
            details.append({
                'tax_code': 'pph21',
                'obj_type': 'Pegawai',
                'count': pph21_count,
                'total_amount': pph21_gross,
                'total_tax': pph21_total,
            })

        conn.close()
        return {
            'year': year,
            'month': month,
            'grand_total': withholding_total + pph21_total,
            'withholding_total': withholding_total,
            'pph21_total': pph21_total,
            'details': details,
            'count': len(details),
            'transaction_count': sum(int(d.get('count') or 0) for d in details),
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
        employee_name = (employee_name or '').strip()
        if not employee_name:
            raise ValueError('Nama pegawai harus diisi')
        try:
            gross_salary = float(gross_salary)
            pph21_amount = float(pph21_amount)
        except (TypeError, ValueError):
            raise ValueError('Nilai gaji/PPh harus berupa angka')
        if gross_salary < 0 or pph21_amount < 0:
            raise ValueError('Nilai gaji/PPh tidak boleh negatif')
        try:
            year = int(year)
            month = int(month)
        except (TypeError, ValueError):
            raise ValueError('Tahun/bulan periode harus angka')
        if month < 1 or month > 12:
            raise ValueError('Bulan periode harus 1-12')
        ptkp_status = str(ptkp_status or 'TK0').upper().strip()
        try:
            dependents = int(dependents or 0)
        except (TypeError, ValueError):
            raise ValueError('Jumlah tanggungan harus angka')
        if dependents < 0:
            raise ValueError('Jumlah tanggungan tidak boleh negatif')

        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pph21_log (employee_name, gross_salary, dependents, ptkp_status,
                                   pph21_amount, period_year, period_month)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_name, gross_salary, dependents, ptkp_status, pph21_amount, year, month))
        conn.commit()
        rid = int(cursor.lastrowid or 0)
        conn.close()
        return rid

    def get_pph21_log(self, limit: int = 100, offset: int = 0,
                      year: Optional[int] = None,
                      month: Optional[int] = None,
                      q: Optional[str] = None) -> Tuple[List[Dict], int]:
        conn = self._conn()
        cursor = conn.cursor()
        conditions = []
        params: List[Any] = []
        if year:
            conditions.append('period_year = ?')
            params.append(int(year))
        if month:
            conditions.append('period_month = ?')
            params.append(int(month))
        if q:
            conditions.append('employee_name LIKE ?')
            params.append(f'%{q.strip()}%')
        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
        cursor.execute(f'SELECT COUNT(*) FROM pph21_log {where}', params)
        total = cursor.fetchone()[0]
        cursor.execute(f"""
            SELECT id, employee_name, gross_salary, dependents, ptkp_status,
                   pph21_amount, period_year, period_month,
                   COALESCE(remittance_status, 'tercatat') as remittance_status,
                   created_at
            FROM pph21_log {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows, total

    def get_total_pph21(self, year: int, month: Optional[int] = None) -> float:
        conn = self._conn()
        cursor = conn.cursor()
        if month:
            cursor.execute("""
                SELECT COALESCE(SUM(pph21_amount), 0)
                FROM pph21_log WHERE period_year = ? AND period_month = ?
            """, (year, month))
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(pph21_amount), 0)
                FROM pph21_log WHERE period_year = ?
            """, (year,))
        total = cursor.fetchone()[0]
        conn.close()
        return float(total or 0)

    def delete_pph21(self, record_id: int) -> bool:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pph21_log WHERE id = ?', (record_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ═══════════════════════════════════════════════════════
    # DOCUMENTS
    # ═══════════════════════════════════════════════════════


    def _normalize_remittance_status(self, status: str) -> str:
        allowed = {'tercatat', 'disetor'}
        value = (status or 'tercatat').strip().lower()
        if value not in allowed:
            raise ValueError('Status setor harus tercatat atau disetor')
        return value

    def set_withholding_remittance(self, record_id: int, status: str) -> bool:
        status = self._normalize_remittance_status(status)
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE withholding SET remittance_status = ? WHERE id = ?',
            (status, int(record_id)),
        )
        ok = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def toggle_withholding_remittance(self, record_id: int) -> str:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(remittance_status, 'tercatat') FROM withholding WHERE id = ?",
            (int(record_id),),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError('Data potongan tidak ditemukan')
        current = (row[0] or 'tercatat').lower()
        nxt = 'disetor' if current != 'disetor' else 'tercatat'
        cursor.execute(
            'UPDATE withholding SET remittance_status = ? WHERE id = ?',
            (nxt, int(record_id)),
        )
        conn.commit()
        conn.close()
        return nxt

    def set_pph21_remittance(self, record_id: int, status: str) -> bool:
        status = self._normalize_remittance_status(status)
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE pph21_log SET remittance_status = ? WHERE id = ?',
            (status, int(record_id)),
        )
        ok = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def toggle_pph21_remittance(self, record_id: int) -> str:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(remittance_status, 'tercatat') FROM pph21_log WHERE id = ?",
            (int(record_id),),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError('Data PPh 21 tidak ditemukan')
        current = (row[0] or 'tercatat').lower()
        nxt = 'disetor' if current != 'disetor' else 'tercatat'
        cursor.execute(
            'UPDATE pph21_log SET remittance_status = ? WHERE id = ?',
            (nxt, int(record_id)),
        )
        conn.commit()
        conn.close()
        return nxt


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
                          status_filter: Optional[str] = None,
                          q: Optional[str] = None) -> Tuple[List[Dict], int]:
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
        if q:
            conditions.append("(title LIKE ? OR COALESCE(notes,'') LIKE ? OR category LIKE ?)")
            like = f"%{q.strip()}%"
            params.extend([like, like, like])

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

    def update_document_status(self, doc_id: int, status: str) -> bool:
        status = (status or '').strip()
        if not status:
            raise ValueError('Status dokumen harus diisi')
        allowed = {'Lengkap', 'Kurang', 'Arsip', 'Dalam Proses'}
        if status not in allowed:
            raise ValueError(f'Status tidak valid: {status}')
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_document(self, doc_id: int) -> Optional[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, category, status, tax_year, tax_month,
                   COALESCE(notes,'') as notes, created_at, file_path
            FROM documents WHERE id = ?
        """, (doc_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_document(self, doc_id: int, title: str, category: str = 'Umum',
                        status: str = 'Lengkap', tax_year: Optional[int] = None,
                        tax_month: Optional[int] = None, notes: str = '') -> bool:
        title = (title or '').strip()
        if not title:
            raise ValueError('Nama dokumen harus diisi')
        category = (category or 'Umum').strip() or 'Umum'
        status = (status or 'Lengkap').strip()
        allowed = {'Lengkap', 'Kurang', 'Arsip', 'Dalam Proses'}
        if status not in allowed:
            raise ValueError(f'Status tidak valid: {status}')
        if tax_month is not None:
            try:
                tax_month = int(tax_month)
            except (TypeError, ValueError):
                raise ValueError('Bulan pajak harus angka 1-12')
            if tax_month < 1 or tax_month > 12:
                raise ValueError('Bulan pajak harus antara 1-12')
        if tax_year is not None:
            try:
                tax_year = int(tax_year)
            except (TypeError, ValueError):
                raise ValueError('Tahun pajak harus angka')

        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents
            SET title = ?, category = ?, status = ?, tax_year = ?, tax_month = ?, notes = ?
            WHERE id = ?
        """, (title, category, status, tax_year, tax_month, notes or '', doc_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

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

    def list_reminders(self, active_only: bool = False) -> List[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        if active_only:
            cursor.execute("""
                SELECT id, title, description, deadline_date, tax_code,
                       is_recurring, is_active, created_at
                FROM tax_reminders
                WHERE is_active = 1
                ORDER BY CAST(deadline_date AS INTEGER), title
            """)
        else:
            cursor.execute("""
                SELECT id, title, description, deadline_date, tax_code,
                       is_recurring, is_active, created_at
                FROM tax_reminders
                ORDER BY CAST(deadline_date AS INTEGER), title
            """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_reminder(self, reminder_id: int) -> Optional[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, deadline_date, tax_code,
                   is_recurring, is_active, created_at
            FROM tax_reminders WHERE id = ?
        """, (reminder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_reminder(self, title: str, deadline_day: Optional[int] = None,
                     description: str = '', tax_code: str = '',
                     is_recurring: bool = True, is_active: bool = True,
                     one_time_date: Optional[str] = None) -> int:
        """
        Add deadline reminder.
        - Recurring monthly: pass deadline_day (1-31), is_recurring=True
        - One-time: pass one_time_date 'YYYY-MM-DD', is_recurring=False
        """
        title = (title or '').strip()
        if not title:
            raise ValueError('Judul deadline harus diisi')

        if is_recurring:
            try:
                day = int(deadline_day)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                raise ValueError('Tanggal deadline harus angka 1-31')
            if day < 1 or day > 31:
                raise ValueError('Tanggal deadline harus antara 1-31')
            stored = str(day)
        else:
            raw = (one_time_date or '').strip()
            if not raw:
                raise ValueError('Tanggal sekali (YYYY-MM-DD) harus diisi untuk deadline non-berulang')
            try:
                date.fromisoformat(raw)
            except ValueError:
                raise ValueError('Format tanggal sekali harus YYYY-MM-DD')
            stored = raw

        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tax_reminders
                (title, description, deadline_date, tax_code, is_recurring, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            description or '',
            stored,
            (tax_code or '').strip() or None,
            1 if is_recurring else 0,
            1 if is_active else 0,
        ))
        conn.commit()
        rid = int(cursor.lastrowid or 0)
        conn.close()
        return rid

    def update_reminder(self, reminder_id: int, title: str,
                        deadline_day: Optional[int] = None,
                        description: str = '', tax_code: str = '',
                        is_recurring: bool = True, is_active: bool = True,
                        one_time_date: Optional[str] = None) -> bool:
        title = (title or '').strip()
        if not title:
            raise ValueError('Judul deadline harus diisi')

        if is_recurring:
            try:
                day = int(deadline_day)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                raise ValueError('Tanggal deadline harus angka 1-31')
            if day < 1 or day > 31:
                raise ValueError('Tanggal deadline harus antara 1-31')
            stored = str(day)
        else:
            raw = (one_time_date or '').strip()
            if not raw:
                raise ValueError('Tanggal sekali (YYYY-MM-DD) harus diisi untuk deadline non-berulang')
            try:
                date.fromisoformat(raw)
            except ValueError:
                raise ValueError('Format tanggal sekali harus YYYY-MM-DD')
            stored = raw

        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tax_reminders
            SET title = ?, description = ?, deadline_date = ?, tax_code = ?,
                is_recurring = ?, is_active = ?
            WHERE id = ?
        """, (
            title,
            description or '',
            stored,
            (tax_code or '').strip() or None,
            1 if is_recurring else 0,
            1 if is_active else 0,
            reminder_id,
        ))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_reminder(self, reminder_id: int) -> bool:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tax_reminders WHERE id = ?", (reminder_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_calendar_deadlines_map(self, year: Optional[int] = None,
                                   month: Optional[int] = None) -> Dict[int, str]:
        """Map day-of-month -> short label for a given month grid."""
        now = date.today()
        year = int(year or now.year)
        month = int(month or now.month)
        reminders = self.list_reminders(active_only=True)
        day_map: Dict[int, List[str]] = {}
        for r in reminders:
            label = (r.get('title') or r.get('tax_code') or 'Deadline').strip()
            short = label if len(label) <= 14 else (label[:12] + '...')
            is_rec = bool(r.get('is_recurring', 1))
            raw = str(r.get('deadline_date') or '').strip()
            if is_rec:
                try:
                    day = int(raw)
                except (TypeError, ValueError):
                    continue
                if day < 1 or day > 31:
                    continue
                # only include if day exists in month
                try:
                    date(year, month, day)
                except ValueError:
                    continue
                day_map.setdefault(day, []).append(short)
            else:
                try:
                    d = date.fromisoformat(raw)
                except ValueError:
                    continue
                if d.year == year and d.month == month:
                    day_map.setdefault(d.day, []).append(short)
        return {d: ' / '.join(labels) for d, labels in sorted(day_map.items())}

    def get_upcoming_deadlines(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming tax deadlines within the specified days."""
        today = date.today()
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, deadline_date, tax_code, is_recurring
            FROM tax_reminders
            WHERE is_active = 1
            ORDER BY id
        """)
        reminders = [dict(r) for r in cursor.fetchall()]
        conn.close()

        deadlines = []
        for r in reminders:
            is_rec = bool(r.get('is_recurring', 1))
            raw = str(r.get('deadline_date') or '').strip()
            candidate_dates = []

            if is_rec:
                try:
                    dl_day = int(raw)
                except (TypeError, ValueError):
                    continue
                if dl_day < 1 or dl_day > 31:
                    continue
                # Recurring monthly: this month + next 2 months
                for m_offset in range(3):
                    y = today.year
                    m = today.month + m_offset
                    if m > 12:
                        m -= 12
                        y += 1
                    try:
                        candidate_dates.append(date(y, m, dl_day))
                    except ValueError:
                        continue
            else:
                try:
                    candidate_dates.append(date.fromisoformat(raw))
                except ValueError:
                    continue

            for dl in candidate_dates:
                diff = (dl - today).days
                if diff < -15:
                    continue
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
                    'is_recurring': is_rec,
                })

        deadlines.sort(key=lambda x: abs(x['days_left']) if x['days_left'] < 0 else x['days_left'])
        return deadlines

    # ═══════════════════════════════════════════════════════
    # DASHBOARD AGGREGATION
    # ═══════════════════════════════════════════════════════

    def get_dashboard_data(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict:
        """Aggregate data for main dashboard for a selected period."""
        now = datetime.now()
        year = int(year or now.year)
        month = int(month or now.month)
        if month < 1 or month > 12:
            month = now.month

        conn = self._conn()
        cursor = conn.cursor()

        # Total PPh due this month (withholding + PPh 21 log)
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0) FROM withholding
            WHERE tax_year = ? AND tax_month = ?
        """, (year, month))
        total_withholding_month = float(cursor.fetchone()[0] or 0)
        cursor.execute("""
            SELECT COALESCE(SUM(pph21_amount), 0) FROM pph21_log
            WHERE period_year = ? AND period_month = ?
        """, (year, month))
        total_pph21_month = float(cursor.fetchone()[0] or 0)
        total_due = total_withholding_month + total_pph21_month

        # Total PPh this year
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0) FROM withholding
            WHERE tax_year = ?
        """, (year,))
        total_withholding_year = float(cursor.fetchone()[0] or 0)
        cursor.execute("""
            SELECT COALESCE(SUM(pph21_amount), 0) FROM pph21_log
            WHERE period_year = ?
        """, (year,))
        total_pph21_year = float(cursor.fetchone()[0] or 0)
        total_year = total_withholding_year + total_pph21_year

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
            'total_withholding_month': total_withholding_month,
            'total_withholding_year': total_withholding_year,
            'total_pph21_month': total_pph21_month,
            'total_pph21_year': total_pph21_year,
            'doc_count': doc_count,
            'doc_by_status': doc_by_status,
            'by_type': by_type,
            'doc_by_category': doc_by_category,
            'month': month,
            'year': year,
        }
