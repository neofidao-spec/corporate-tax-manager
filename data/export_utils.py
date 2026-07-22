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


TAX_CODE_LABELS = {
    'pph23': 'PPh 23',
    'pph26': 'PPh 26',
    'pph_final': 'PPh Final',
    'pph21': 'PPh 21',
}


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


def default_export_filename(prefix: str = 'export', when: Optional[date] = None) -> str:
    d = when or date.today()
    return f'{prefix}_{d.isoformat()}.csv'


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


def withholding_csv_rows(records: Iterable[Dict[str, Any]]) -> List[List[Any]]:
    rows: List[List[Any]] = [[
        'ID', 'Vendor', 'Jumlah Bruto', 'Jenis Objek', 'Jenis Pajak',
        'Tarif', 'PPh', 'Deskripsi', 'Tgl Input', 'Tahun', 'Bulan',
    ]]
    for r in records:
        rows.append([
            r.get('id'),
            r.get('vendor'),
            r.get('amount'),
            r.get('obj_type'),
            r.get('tax_code'),
            r.get('tariff_label'),
            r.get('pph_amount'),
            r.get('description'),
            r.get('created_at'),
            r.get('tax_year'),
            r.get('tax_month'),
        ])
    return rows


def period_report_csv_rows(
    summary: Dict[str, Any],
    year: int,
    month: int,
    labels: Optional[Dict[str, str]] = None,
) -> List[List[Any]]:
    labels = labels or TAX_CODE_LABELS
    rows: List[List[Any]] = [[
        'Tahun', 'Bulan', 'Kode Pajak', 'Label', 'Jenis Objek',
        'Jumlah', 'Total Bruto', 'Total PPh',
    ]]
    for d in summary.get('details') or []:
        code = d.get('tax_code') or ''
        rows.append([
            year,
            month,
            code,
            labels.get(code, code),
            d.get('obj_type') or '',
            d.get('count') or 0,
            d.get('total_amount') or 0,
            d.get('total_tax') or 0,
        ])
    rows.append([])
    rows.append([
        '', '', 'TOTAL', '', '',
        summary.get('transaction_count') or 0, '',
        summary.get('grand_total') or 0,
    ])
    return rows


def export_pph21_csv(
    records: Iterable[Dict[str, Any]],
    directory: str,
    filename: Optional[str] = None,
) -> Tuple[str, int, float]:
    """Write PPh 21 CSV. Returns (path, row_count, pph_total)."""
    recs = list(records)
    name = filename or default_export_filename('pph21_export')
    path = os.path.join(directory, name)
    write_csv_file(path, pph21_csv_rows(recs))
    total = sum(float(r.get('pph21_amount') or 0) for r in recs)
    return path, len(recs), total


def export_withholding_csv(
    records: Iterable[Dict[str, Any]],
    directory: str,
    filename: Optional[str] = None,
) -> Tuple[str, int, float]:
    """Write withholding CSV. Returns (path, row_count, pph_total)."""
    recs = list(records)
    name = filename or default_export_filename('pph_export')
    path = os.path.join(directory, name)
    write_csv_file(path, withholding_csv_rows(recs))
    total = sum(float(r.get('pph_amount') or 0) for r in recs)
    return path, len(recs), total


def export_period_report_csv(
    summary: Dict[str, Any],
    year: int,
    month: int,
    directory: str,
    filename: Optional[str] = None,
) -> Tuple[str, int, float]:
    """Write period report CSV. Returns (path, detail_count, grand_total)."""
    name = filename or f'laporan_periode_{year}_{month:02d}.csv'
    path = os.path.join(directory, name)
    rows = period_report_csv_rows(summary, year, month)
    write_csv_file(path, rows)
    details = summary.get('details') or []
    total = float(summary.get('grand_total') or 0)
    return path, len(details), total
