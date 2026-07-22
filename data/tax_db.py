"""
Tax Database — Corporate Tax Manager
SQLite database untuk:
- Log transaksi potongan PPh 23/26
- Manajemen dokumen perpajakan
- Ringkasan pajak per periode
"""

import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tax_data.db')


class TaxDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_tables(self):
        """Create tables if they don't exist."""
        conn = self._conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withholding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL,
                obj_type TEXT NOT NULL,
                tariff_label TEXT,
                pph_amount REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                tax_year INTEGER NOT NULL DEFAULT (CAST(strftime('%Y', 'now') AS INTEGER)),
                tax_month INTEGER NOT NULL DEFAULT (CAST(strftime('%m', 'now') AS INTEGER))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Umum',
                status TEXT NOT NULL DEFAULT 'Lengkap',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pph21_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                gross_salary REAL NOT NULL,
                dependents INTEGER DEFAULT 0,
                pph21_amount REAL NOT NULL,
                period_year INTEGER NOT NULL,
                period_month INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)

        conn.commit()
        conn.close()

    # ──── WITHHOLDING (PPh 23/26) ────

    def add_withholding(self, vendor: str, amount: float, obj_type: str,
                        tariff_label: str = '2%') -> int:
        conn = self._conn()
        cursor = conn.cursor()

        # Calculate PPh amount from tariff label
        tariff_map = {
            '2%': 0.02, '15%': 0.15, '20%': 0.20,
            '2': 0.02, '15': 0.15, '20': 0.20,
        }
        tariff = tariff_map.get(tariff_label.strip(), 0.02)
        pph_amount = amount * tariff

        now = datetime.now()
        cursor.execute("""
            INSERT INTO withholding (vendor, amount, obj_type, tariff_label, pph_amount,
                                     created_at, tax_year, tax_month)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)
        """, (vendor, amount, obj_type, tariff_label, pph_amount,
              now.year, now.month))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_all_withholding(self, limit: int = 100) -> list:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, vendor, amount, obj_type, pph_amount, created_at
            FROM withholding
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [list(r) for r in rows]

    def get_total_pph23(self, year: int, month: int) -> float:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0)
            FROM withholding
            WHERE tax_year = ? AND tax_month = ?
        """, (year, month))
        total = cursor.fetchone()[0]
        conn.close()
        return total

    def get_total_pph_final(self, year: int) -> float:
        """Placeholder — PPh final from other sources."""
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(pph_amount), 0)
            FROM withholding
            WHERE tax_year = ?
        """, (year,))
        total = cursor.fetchone()[0]
        conn.close()
        return total

    def delete_withholding(self, record_id: int):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM withholding WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()

    # ──── PPh 21 LOG ────

    def add_pph21(self, employee_name: str, gross_salary: float,
                  dependents: int, pph21_amount: float,
                  year: int, month: int) -> int:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pph21_log (employee_name, gross_salary, dependents,
                                   pph21_amount, period_year, period_month)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_name, gross_salary, dependents, pph21_amount, year, month))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_total_pph21(self, year: int) -> float:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(pph21_amount), 0)
            FROM pph21_log
            WHERE period_year = ?
        """, (year,))
        total = cursor.fetchone()[0]
        conn.close()
        return total

    # ──── DOCUMENTS ────

    def add_document(self, title: str, category: str = 'Umum',
                     status: str = 'Lengkap', notes: str = '') -> int:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (title, category, status, notes)
            VALUES (?, ?, ?, ?)
        """, (title, category, status, notes))
        conn.commit()
        rid = cursor.lastrowid
        conn.close()
        return rid

    def get_all_documents(self, limit: int = 100) -> list:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, category, status, created_at
            FROM documents
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [list(r) for r in rows]

    def delete_document(self, doc_id: int):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
