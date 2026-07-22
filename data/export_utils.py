"""
CSV export helpers (pure Python, no Kivy dependency).
Shared by web routes and Android app.
"""
from __future__ import annotations

import csv
import os
from datetime import date
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def pph21_csv_rows(records: Iterable[Dict[str, Any]]) -> List[List[Any]]:
    rows: List[List[Any]] = [[
        'ID', 'Pegawai', 'Gaji Bruto', 'Tanggungan', 'PTKP',
        'PPh 21', 'Tahun', 'Bulan', 'Tgl Input',
    ]]
    for r in records:
        rows.append([
            r.get('id'),
            r.get('employee_name'),
            r.get('gross_salary'),
            r.get('dependents'),
            r.get('ptkp_status'),
            r.get('pph21_amount'),
            r.get('period_year'),
            r.get('period_month'),
            r.get('created_at'),
        ])
    return rows


def render_csv(rows: Sequence[Sequence[Any]]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def write_csv_file(path: str, rows: Sequence[Sequence[Any]]) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    content = render_csv(rows)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    return path


def default_export_filename(prefix: str = 'pph21_export', when: Optional[date] = None) -> str:
    d = when or date.today()
    return f'{prefix}_{d.isoformat()}.csv'


def export_pph21_csv(
    records: Iterable[Dict[str, Any]],
    directory: str,
    filename: Optional[str] = None,
) -> Tuple[str, int, float]:
    """Write PPh 21 CSV. Returns (path, row_count, pph_total)."""
    recs = list(records)
    name = filename or default_export_filename()
    path = os.path.join(directory, name)
    write_csv_file(path, pph21_csv_rows(recs))
    total = sum(float(r.get('pph21_amount') or 0) for r in recs)
    return path, len(recs), total
