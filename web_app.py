"""
Corporate Tax Manager — Web Application
Flask app dengan blueprint architecture.
Membantu tugas bagian pajak perusahaan secara komprehensif.
"""

import os
import sys
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, g, Response,
)

# Ensure data module is importable
sys.path.insert(0, os.path.dirname(__file__))

from data.tax_calculator import TaxCalculator
from data.tax_db import TaxDB

calc = TaxCalculator()


# ─── App Factory ───
def create_app(testing=False):
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY') or ('test-secret' if testing else os.urandom(24).hex())
    app.config['DATABASE'] = os.path.join(
        os.path.dirname(__file__), 'tax_data.db')

    if testing:
        app.config['TESTING'] = True
        app.config['DATABASE'] = os.path.join(
            os.path.dirname(__file__), 'test_tax.db')

    # Init DB on first request
    with app.app_context():
        TaxDB(app.config['DATABASE']).init_tables()

    # ─── Request lifecycle ───
    @app.before_request
    def before_request():
        g.db = TaxDB(app.config['DATABASE'])

    @app.teardown_appcontext
    def teardown(exception):
        pass

    @app.context_processor
    def inject_now():
        ctx = {'now': datetime.now(), 'today': date.today()}
        try:
            db = TaxDB(app.config['DATABASE'])
            ds = db.get_dashboard_data(year=date.today().year, month=date.today().month)
            ctx['nav_doc_count'] = ds.get('doc_count', 0) or 0
            ctx['nav_outstanding'] = ds.get('outstanding_count', 0) or 0
        except Exception:
            ctx['nav_doc_count'] = 0
            ctx['nav_outstanding'] = 0
        return ctx

    # ══════════════════════════════════════════════════
    # ROUTES: Dashboard
    # ══════════════════════════════════════════════════

    @app.route('/')
    def index():
        now = date.today()
        year = request.args.get('year', now.year, type=int) or now.year
        month = request.args.get('month', now.month, type=int) or now.month
        if month < 1 or month > 12:
            month = now.month

        data = g.db.get_dashboard_data(year=year, month=month)
        deadline_window = request.args.get('window', 30, type=int) or 30
        if deadline_window not in (7, 30, 60):
            deadline_window = 30
        deadlines = g.db.get_upcoming_deadlines(days_ahead=deadline_window)
        yearly = g.db.get_yearly_summary(data['year'])

        # ── Progress masa (alur): catat → PPh21 → setor → lapor ──
        wh_count = data.get('total_withholding_count', 0) or 0
        p21_count = data.get('total_pph21_count', 0) or 0
        outstanding = data.get('outstanding_count', 0) or 0
        steps_done = 0
        if wh_count > 0:
            steps_done += 1
        if p21_count > 0:
            steps_done += 1
        if wh_count > 0 and p21_count > 0 and outstanding == 0:
            steps_done += 1
        progress_pct = min(steps_done * 33, 100)
        progress_steps = [
            {'label': 'Catat potongan', 'done': wh_count > 0},
            {'label': 'Rekonsiliasi PPh 21', 'done': p21_count > 0},
            {'label': 'Setor seluruhnya', 'done': wh_count > 0 and p21_count > 0 and outstanding == 0},
        ]

        # Previous month comparison
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        prev_data = g.db.get_dashboard_data(year=prev_y, month=prev_m)
        curr_due = float(data.get('total_due_this_month') or 0)
        prev_due = float(prev_data.get('total_due_this_month') or 0)
        delta = curr_due - prev_due
        if prev_due > 0:
            delta_pct = (delta / prev_due) * 100
        else:
            delta_pct = 100.0 if curr_due > 0 else 0.0
        comparison = {
            'prev_year': prev_y,
            'prev_month': prev_m,
            'prev_due': prev_due,
            'delta': delta,
            'delta_pct': delta_pct,
            'direction': 'up' if delta > 0 else ('down' if delta < 0 else 'flat'),
        }

        # Aggregate monthly totals for chart (1..12)
        month_totals = {m: 0.0 for m in range(1, 13)}
        for row in yearly or []:
            try:
                m = int(row.get('tax_month') or 0)
                if 1 <= m <= 12:
                    month_totals[m] += float(row.get('total_tax') or 0)
            except (TypeError, ValueError):
                continue
        chart_max = max(month_totals.values()) if month_totals else 0
        chart = []
        chart_data_withholding = {m: 0.0 for m in range(1, 13)}
        chart_data_pph21 = {m: 0.0 for m in range(1, 13)}
        for row in yearly or []:
            try:
                m = int(row.get('tax_month') or 0)
                if 1 <= m <= 12:
                    tc = (row.get('tax_code') or '').lower()
                    v = float(row.get('total_tax') or 0)
                    if tc == 'pph21':
                        chart_data_pph21[m] += v
                    else:
                        chart_data_withholding[m] += v
            except (TypeError, ValueError):
                continue
        labels = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
                  7: 'Jul', 8: 'Agu', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'}
        for m in range(1, 13):
            val = month_totals[m]
            pct = (val / chart_max * 100) if chart_max > 0 else 0
            chart.append({
                'month': m,
                'label': labels[m],
                'total': val,
                'pct': max(pct, 2 if val > 0 else 0),
            })

        # Period navigation
        next_m = month + 1 if month < 12 else 1
        next_y = year if month < 12 else year + 1
        urgent = [d for d in (deadlines or []) if d.get('status') in ('LEWAT', 'SEGERA')]

        return render_template(
            'index.html',
            dash=data,
            deadlines=deadlines,
            deadline_window=deadline_window,
            urgent_deadlines=urgent,
            yearly=yearly,
            chart=chart,
            chart_max=chart_max,
            chart_data_withholding=chart_data_withholding,
            chart_data_pph21=chart_data_pph21,
            selected_year=year,
            selected_month=month,
            prev_y=prev_y,
            prev_m=prev_m,
            next_y=next_y,
            next_m=next_m,
            month_labels=labels,
            progress_pct=progress_pct,
            progress_steps=progress_steps,
            comparison=comparison,
        )

    # ══════════════════════════════════════════════════
    # ROUTES: Calculator
    # ══════════════════════════════════════════════════

    @app.route('/calculator', methods=['GET', 'POST'])
    def calculator():
        results = {}
        calc_type = 'pph21'

        if request.method == 'POST':
            calc_type = request.form.get('calc_type', 'pph21')
            try:
                if calc_type == 'pph21':
                    gross = float(request.form.get('gross', 0))
                    status = request.form.get('ptkp_status', 'TK0')
                    results = calc.pph21(gross, status)

                elif calc_type == 'pph21_nonpegawai':
                    gross = float(request.form.get('gross_non', 0))
                    status = request.form.get('ptkp_status_non', 'TK0')
                    results = calc.pph21_non_pegawai(gross, status)

                elif calc_type == 'pph23':
                    amount = float(request.form.get('amount', 0))
                    obj_type = request.form.get('obj_type', 'Jasa')
                    results = calc.pph23(amount, obj_type)

                elif calc_type == 'pph26':
                    amount = float(request.form.get('amount_26', 0))
                    obj_type = request.form.get('obj_type_26', 'Jasa')
                    have_npwp = request.form.get('have_npwp') == 'on'
                    results = calc.pph26(amount, obj_type, have_npwp=have_npwp)

                elif calc_type == 'ppn':
                    price = float(request.form.get('price', 0))
                    tariff = float(request.form.get('tariff', 11))
                    include_ppn = request.form.get('include_ppn') == 'on'
                    results = calc.ppn(price, tariff, include_ppn=include_ppn)

                elif calc_type == 'ppn_impor':
                    nilai = float(request.form.get('nilai_impor', 0))
                    bea = float(request.form.get('bea_masuk', 0))
                    results = calc.ppn_impor(nilai, bea)

                elif calc_type == 'pph_badan':
                    profit = float(request.form.get('profit', 0))
                    omzet = float(request.form.get('omzet', 0))
                    results = calc.pph_badan(profit, omzet)

                elif calc_type == 'pph_final_sewa':
                    sewa = float(request.form.get('sewa', 0))
                    results = calc.pph_final_sewa_tanah(sewa)

                elif calc_type == 'pph_final_konstruksi':
                    nilai = float(request.form.get('konstruksi_nilai', 0))
                    rank = request.form.get('license_rank', 'lainnya')
                    results = calc.pph_final_konstruksi(nilai, rank)

                elif calc_type == 'pph_final_pesangon':
                    nilai = float(request.form.get('pesangon', 0))
                    results = calc.pph_final_pesangon(nilai)

                elif calc_type == 'pph_final_penjualan':
                    harga = float(request.form.get('harga_jual', 0))
                    results = calc.pph_final_penjualan_tanah(harga)

                elif calc_type == 'pph_final_bunga':
                    bunga = float(request.form.get('bunga_deposito', 0))
                    results = calc.pph_final_bunga_deposito(bunga)

                elif calc_type == 'pph22_impor':
                    nilai = float(request.form.get('nilai_p22', 0))
                    api = request.form.get('have_api') == 'on'
                    results = calc.pph22_impor(nilai, api)

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Kesalahan perhitungan: {str(e)}', 'error')

        return render_template(
            'calculator.html',
            results=results,
            calc_type=calc_type,
            result_summary=calc.summary(results) if results else '',
        )

    # ══════════════════════════════════════════════════
    # ROUTES: Withholding (PPh 23/26/Final)
    # ══════════════════════════════════════════════════

    @app.route('/withholding')
    def withholding():
        page = request.args.get('page', 1, type=int)
        per_page = 25
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        tax_code = request.args.get('tax_code')
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None

        records, total = g.db.get_all_withholding(
            limit=per_page, offset=(page - 1) * per_page,
            year=year, month=month, tax_code=tax_code, remit=remit,
        )
        total_pages = max(1, (total + per_page - 1) // per_page)
        return render_template(
            'withholding.html',
            records=records,
            page=page,
            total_pages=total_pages,
            total=total,
            year=year,
            month=month,
            tax_code=tax_code,
            remit=remit,
        )

    @app.route('/withholding/add', methods=['POST'])
    def add_withholding():
        try:
            vendor = request.form.get('vendor', '').strip()
            if not vendor:
                flash('Nama vendor harus diisi', 'error')
                return redirect(url_for('withholding'))
            amount = float(request.form.get('amount', 0))
            if amount < 0:
                flash('Jumlah bruto tidak boleh negatif', 'error')
                return redirect(url_for('withholding'))
            obj_type = request.form.get('obj_type', 'Jasa')
            tax_code = request.form.get('tax_code', 'pph23')
            tariff_label = request.form.get('tariff', '2%')
            description = request.form.get('description', '')

            rid = g.db.add_withholding(vendor, amount, obj_type, tax_code, tariff_label, description)
            # Read back stored amount for flash (DB is source of truth)
            records, _ = g.db.get_all_withholding(limit=1)
            pph_val = records[0]['pph_amount'] if records else 0
            flash(f'Data tersimpan: {vendor} — Rp {float(pph_val):,.0f}', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal menyimpan: {str(e)}', 'error')

        return redirect(url_for('withholding'))

    @app.route('/withholding/delete/<int:rid>', methods=['POST'])
    def delete_withholding(rid):
        g.db.delete_withholding(rid)
        flash('Data dihapus', 'success')
        return redirect(url_for('withholding'))

    @app.route('/withholding/<int:rid>/remit', methods=['POST'])
    def toggle_withholding_remit(rid):
        try:
            nxt = g.db.toggle_withholding_remittance(rid)
            label = 'Disetor' if nxt == 'disetor' else 'Tercatat'
            flash(f'Status potongan diubah ke {label}', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal mengubah status setor: {e}', 'error')
        # preserve filters when possible
        year = request.form.get('year') or request.args.get('year')
        month = request.form.get('month') or request.args.get('month')
        tax_code = request.form.get('tax_code') or request.args.get('tax_code')
        return redirect(url_for('withholding', year=year, month=month, tax_code=tax_code))

    # ══════════════════════════════════════════════════
    # ROUTES: PPh 21 Log (payroll)
    # ══════════════════════════════════════════════════

    @app.route('/pph21')
    def pph21_log():
        page = request.args.get('page', 1, type=int)
        per_page = 25
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        q = (request.args.get('q') or '').strip() or None
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None
        records, total = g.db.get_pph21_log(
            limit=per_page,
            offset=(page - 1) * per_page,
            year=year,
            month=month,
            q=q,
            remit=remit,
        )
        total_pages = max(1, (total + per_page - 1) // per_page)
        year_total = g.db.get_total_pph21(year) if year else g.db.get_total_pph21(date.today().year)
        return render_template(
            'pph21.html',
            records=records,
            page=page,
            total_pages=total_pages,
            total=total,
            year=year,
            month=month,
            q=q or '',
            remit=remit,
            year_total=year_total,
            now=date.today(),
        )

    @app.route('/pph21/add', methods=['POST'])
    def add_pph21():
        try:
            name = request.form.get('employee_name', '').strip()
            gross = float(request.form.get('gross_salary', 0))
            ptkp = request.form.get('ptkp_status', 'TK0')
            year = request.form.get('year', type=int) or date.today().year
            month = request.form.get('month', type=int) or date.today().month
            # Auto-calc PPh 21 from calculator if not provided
            pph_raw = request.form.get('pph21_amount', '').strip()
            if pph_raw:
                pph_amount = float(pph_raw)
            else:
                result = calc.pph21(gross, ptkp)
                pph_amount = float(result.get('pph_monthly') or result.get('pph') or 0)
            dependents_map = {
                'TK0': 0, 'TK1': 1, 'TK2': 2, 'TK3': 3,
                'K0': 0, 'K1': 1, 'K2': 2, 'K3': 3,
            }
            dependents = dependents_map.get(str(ptkp).upper(), 0)
            g.db.add_pph21(
                employee_name=name,
                gross_salary=gross,
                dependents=dependents,
                ptkp_status=ptkp,
                pph21_amount=pph_amount,
                year=year,
                month=month,
            )
            flash(f'PPh 21 tersimpan: {name} — Rp {pph_amount:,.0f}', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal menyimpan: {e}', 'error')
        return redirect(url_for('pph21_log'))

    @app.route('/pph21/delete/<int:rid>', methods=['POST'])
    def delete_pph21(rid):
        try:
            ok = g.db.delete_pph21(rid)
            flash('Data dihapus' if ok else 'Data tidak ditemukan',
                  'success' if ok else 'error')
        except Exception as e:
            flash(f'Gagal menghapus: {e}', 'error')
        return redirect(url_for('pph21_log'))

    @app.route('/pph21/<int:rid>/remit', methods=['POST'])
    def toggle_pph21_remit(rid):
        try:
            nxt = g.db.toggle_pph21_remittance(rid)
            label = 'Disetor' if nxt == 'disetor' else 'Tercatat'
            flash(f'Status PPh 21 diubah ke {label}', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal mengubah status setor: {e}', 'error')
        year = request.form.get('year') or request.args.get('year')
        month = request.form.get('month') or request.args.get('month')
        q = request.form.get('q') or request.args.get('q')
        remit = request.form.get('remit') or request.args.get('remit')
        return redirect(url_for('pph21_log', year=year, month=month, q=q, remit=remit))

    @app.route('/pph21/export')
    def export_pph21():
        from data.export_utils import pph21_csv_rows, render_csv
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        q = (request.args.get('q') or '').strip() or None
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None
        records, _ = g.db.get_pph21_log(
            limit=10000, offset=0, year=year, month=month, q=q, remit=remit,
        )
        return Response(
            render_csv(pph21_csv_rows(records)),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=pph21_export.csv'},
        )

    @app.route('/pph21/print')
    def print_pph21():
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        q = (request.args.get('q') or '').strip() or None
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None
        records, total = g.db.get_pph21_log(
            limit=10000, offset=0, year=year, month=month, q=q, remit=remit,
        )
        bruto_total = sum(float(r.get('gross_salary') or 0) for r in records)
        pph_total = sum(float(r.get('pph21_amount') or 0) for r in records)
        filter_bits = []
        if year:
            filter_bits.append(f'Tahun {year}')
        if month:
            filter_bits.append(f'Bulan {month}')
        if q:
            filter_bits.append(f'Cari: {q}')
        if remit:
            filter_bits.append('Belum disetor' if remit == 'tercatat' else 'Sudah disetor')
        filter_summary = ' · '.join(filter_bits) if filter_bits else 'Semua periode'
        return render_template(
            'print_pph21.html',
            records=records,
            total=total,
            bruto_total=bruto_total,
            pph_total=pph_total,
            year=year,
            month=month,
            q=q or '',
            filter_summary=filter_summary,
            generated_at=datetime.now(),
        )

    @app.route('/reports/period')
    def period_report():
        now = date.today()
        year = request.args.get('year', now.year, type=int) or now.year
        month = request.args.get('month', now.month, type=int) or now.month
        if month < 1 or month > 12:
            month = now.month
        try:
            summary = g.db.get_summary_by_period(year, month)
        except ValueError as e:
            flash(str(e), 'error')
            summary = {
                'year': year, 'month': month, 'grand_total': 0,
                'withholding_total': 0, 'pph21_total': 0,
                'details': [], 'count': 0, 'transaction_count': 0,
            }
        labels = {1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
                  7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'}
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        next_m = month + 1 if month < 12 else 1
        next_y = year if month < 12 else year + 1
        return render_template(
            'period_report.html',
            summary=summary,
            month_labels=labels,
            selected_year=year,
            selected_month=month,
            prev_y=prev_y,
            prev_m=prev_m,
            next_y=next_y,
            next_m=next_m,
        )

    @app.route('/reports/period/print')
    def print_period_report():
        now = date.today()
        year = request.args.get('year', now.year, type=int) or now.year
        month = request.args.get('month', now.month, type=int) or now.month
        if month < 1 or month > 12:
            month = now.month
        try:
            summary = g.db.get_summary_by_period(year, month)
        except ValueError:
            summary = {
                'year': year, 'month': month, 'grand_total': 0,
                'withholding_total': 0, 'pph21_total': 0,
                'details': [], 'count': 0, 'transaction_count': 0,
            }
        labels = {1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
                  7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'}
        return render_template(
            'print_period_report.html',
            summary=summary,
            month_labels=labels,
            selected_year=year,
            selected_month=month,
            generated_at=datetime.now(),
        )

    @app.route('/reports/period/export')
    def export_period_report():
        now = date.today()
        year = request.args.get('year', now.year, type=int) or now.year
        month = request.args.get('month', now.month, type=int) or now.month
        if month < 1 or month > 12:
            month = now.month
        try:
            summary = g.db.get_summary_by_period(year, month)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('period_report', year=year, month=month))

        from data.export_utils import period_report_csv_rows, render_csv
        filename = f'laporan_periode_{year}_{month:02d}.csv'
        return Response(
            render_csv(period_report_csv_rows(summary, year, month)),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}'},
        )

    @app.route('/withholding/export')
    def export_withholding():
        from data.export_utils import withholding_csv_rows, render_csv
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        tax_code = request.args.get('tax_code')
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None
        records, _ = g.db.get_all_withholding(
            limit=10000, year=year, month=month, tax_code=tax_code, remit=remit,
        )
        return Response(
            render_csv(withholding_csv_rows(records)),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=pph_export.csv'},
        )

    # ══════════════════════════════════════════════════
    # ROUTES: Documents
    # ══════════════════════════════════════════════════

    @app.route('/documents')
    def documents():
        page = request.args.get('page', 1, type=int)
        per_page = 20
        category = request.args.get('category')
        status_filter = request.args.get('status')
        q = (request.args.get('q') or '').strip() or None

        docs, total = g.db.get_all_documents(
            limit=per_page, offset=(page - 1) * per_page,
            category=category, status_filter=status_filter, q=q,
        )
        total_pages = max(1, (total + per_page - 1) // per_page)
        return render_template(
            'documents.html',
            docs=docs,
            page=page,
            total_pages=total_pages,
            total=total,
            category=category,
            status_filter=status_filter,
            q=q or '',
        )

    @app.route('/documents/add', methods=['POST'])
    def add_document():
        try:
            title = request.form.get('title', '').strip()
            if not title:
                flash('Nama dokumen harus diisi', 'error')
                return redirect(url_for('documents'))
            category = request.form.get('category', 'Umum')
            status = request.form.get('status', 'Lengkap')
            tax_year = request.form.get('tax_year', type=int)
            tax_month = request.form.get('tax_month', type=int)
            notes = request.form.get('notes', '')

            g.db.add_document(title, category, status, tax_year, tax_month, notes)
            flash('Dokumen berhasil dicatat!', 'success')
        except Exception as e:
            flash(f'Gagal: {str(e)}', 'error')
        return redirect(url_for('documents'))

    @app.route('/documents/<int:did>/status', methods=['POST'])
    def update_document_status(did):
        try:
            status = request.form.get('status', '').strip()
            ok = g.db.update_document_status(did, status)
            if ok:
                flash(f'Status dokumen diubah ke {status}', 'success')
            else:
                flash('Dokumen tidak ditemukan', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal mengubah status: {str(e)}', 'error')
        return redirect(url_for(
            'documents',
            page=request.args.get('page', 1),
            category=request.args.get('category'),
            status=request.args.get('status'),
            q=request.args.get('q'),
        ))

    @app.route('/documents/<int:did>/edit', methods=['POST'])
    def edit_document(did):
        try:
            title = request.form.get('title', '').strip()
            category = request.form.get('category', 'Umum')
            status = request.form.get('status', 'Lengkap')
            tax_year = request.form.get('tax_year', type=int)
            tax_month = request.form.get('tax_month', type=int)
            notes = request.form.get('notes', '')
            ok = g.db.update_document(
                did, title=title, category=category, status=status,
                tax_year=tax_year, tax_month=tax_month, notes=notes,
            )
            if ok:
                flash('Dokumen berhasil diperbarui', 'success')
            else:
                flash('Dokumen tidak ditemukan', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal memperbarui: {str(e)}', 'error')
        return redirect(url_for(
            'documents',
            page=request.args.get('page', 1),
            category=request.args.get('category'),
            status=request.args.get('status'),
            q=request.args.get('q'),
        ))

    @app.route('/documents/delete/<int:did>', methods=['POST'])
    def delete_document(did):
        g.db.delete_document(did)
        flash('Dokumen dihapus', 'success')
        return redirect(url_for('documents'))

    @app.route('/withholding/print')
    def print_withholding():
        """Print-friendly statement preview of withholding log."""
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        tax_code = request.args.get('tax_code')
        remit = (request.args.get('remit') or '').strip().lower() or None
        if remit not in (None, 'tercatat', 'disetor'):
            remit = None
        records, total = g.db.get_all_withholding(
            limit=10000, year=year, month=month, tax_code=tax_code, remit=remit,
        )
        grand_total = sum(float(r.get('pph_amount') or 0) for r in records)
        bruto_total = sum(float(r.get('amount') or 0) for r in records)
        tax_labels = {
            'pph23': 'PPh 23', 'pph26': 'PPh 26',
            'pph_final': 'PPh Final', 'pph21': 'PPh 21',
        }
        filter_bits = []
        if year:
            filter_bits.append(f"Tahun {year}")
        if month:
            filter_bits.append(f"Bulan {month}")
        if tax_code:
            filter_bits.append(tax_labels.get(tax_code, tax_code))
        filter_summary = ' · '.join(filter_bits) if filter_bits else 'Semua periode & jenis'
        return render_template(
            'print_withholding.html',
            records=records,
            total=total,
            grand_total=grand_total,
            bruto_total=bruto_total,
            year=year,
            month=month,
            tax_code=tax_code,
            filter_summary=filter_summary,
            generated_at=datetime.now(),
        )

    # ══════════════════════════════════════════════════
    # ROUTES: Calendar
    # ══════════════════════════════════════════════════

    @app.route('/calendar')
    def calendar_view():
        import calendar as cal_mod
        now = date.today()
        y = request.args.get('year', now.year, type=int)
        m = request.args.get('month', now.month, type=int)
        if m < 1 or m > 12:
            m = now.month

        cal = cal_mod.monthcalendar(y, m)
        month_name = cal_mod.month_name[m]
        # User-configurable deadlines from DB (fallback empty)
        try:
            deadlines_map = g.db.get_calendar_deadlines_map(year=y, month=m)
            reminders = g.db.list_reminders(active_only=False)
        except Exception:
            deadlines_map = {10: 'PPN', 15: 'PPh Final', 20: 'PPh 21/23', 21: 'PPh 26'}
            reminders = []

        # Navigation
        prev_m = m - 1 if m > 1 else 12
        prev_y = y if m > 1 else y - 1
        next_m = m + 1 if m < 12 else 1
        next_y = y if m < 12 else y + 1

        return render_template(
            'calendar.html',
            cal=cal,
            month_name=month_name,
            year=y,
            month=m,
            today=now,
            deadlines=deadlines_map,
            reminders=reminders,
            prev_m=prev_m,
            prev_y=prev_y,
            next_m=next_m,
            next_y=next_y,
        )

    @app.route('/calendar/reminders/add', methods=['POST'])
    def add_calendar_reminder():
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '')
            tax_code = request.form.get('tax_code', '')
            is_active = request.form.get('is_active') == 'on'
            # Checkbox: only present when checked. No default 'on'.
            is_recurring = request.form.get('is_recurring') == 'on'
            day = request.form.get('deadline_day', type=int)
            one_time_date = request.form.get('one_time_date', '').strip() or None
            g.db.add_reminder(
                title=title,
                deadline_day=day if is_recurring else None,
                description=description,
                tax_code=tax_code,
                is_recurring=is_recurring,
                is_active=is_active,
                one_time_date=None if is_recurring else one_time_date,
            )
            flash('Deadline ditambahkan', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal menambah deadline: {e}', 'error')
        y = request.args.get('year') or request.form.get('year')
        m = request.args.get('month') or request.form.get('month')
        return redirect(url_for('calendar_view', year=y, month=m))

    @app.route('/calendar/reminders/<int:rid>/edit', methods=['POST'])
    def edit_calendar_reminder(rid):
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '')
            tax_code = request.form.get('tax_code', '')
            is_active = request.form.get('is_active') == 'on'
            is_recurring = request.form.get('is_recurring') == 'on'
            day = request.form.get('deadline_day', type=int)
            one_time_date = request.form.get('one_time_date', '').strip() or None
            ok = g.db.update_reminder(
                rid,
                title=title,
                deadline_day=day if is_recurring else None,
                description=description,
                tax_code=tax_code,
                is_recurring=is_recurring,
                is_active=is_active,
                one_time_date=None if is_recurring else one_time_date,
            )
            if ok:
                flash('Deadline diperbarui', 'success')
            else:
                flash('Deadline tidak ditemukan', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal memperbarui: {e}', 'error')
        y = request.args.get('year') or request.form.get('year')
        m = request.args.get('month') or request.form.get('month')
        return redirect(url_for('calendar_view', year=y, month=m))

    @app.route('/calendar/reminders/<int:rid>/delete', methods=['POST'])
    def delete_calendar_reminder(rid):
        try:
            ok = g.db.delete_reminder(rid)
            flash('Deadline dihapus' if ok else 'Deadline tidak ditemukan',
                  'success' if ok else 'error')
        except Exception as e:
            flash(f'Gagal menghapus: {e}', 'error')
        y = request.args.get('year') or request.form.get('year')
        m = request.args.get('month') or request.form.get('month')
        return redirect(url_for('calendar_view', year=y, month=m))

    # ══════════════════════════════════════════════════
    # ROUTES: API (JSON)
    # ══════════════════════════════════════════════════

    @app.route('/api/dashboard')
    def api_dashboard():
        data = g.db.get_dashboard_data()
        deadlines = g.db.get_upcoming_deadlines()
        data['deadlines'] = deadlines
        return jsonify(data)

    @app.route('/api/calculate', methods=['POST'])
    def api_calculate():
        """JSON API endpoint for calculations."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        calc_type = data.get('type', 'pph21')
        try:
            if calc_type == 'pph21':
                result = calc.pph21(
                    float(data.get('gross', 0)),
                    data.get('ptkp_status', 'TK0'),
                )
            elif calc_type == 'pph23':
                result = calc.pph23(
                    float(data.get('amount', 0)),
                    data.get('obj_type', 'Jasa'),
                )
            elif calc_type == 'ppn':
                result = calc.ppn(
                    float(data.get('price', 0)),
                    float(data.get('tariff', 11)),
                    data.get('include_ppn', False),
                )
            elif calc_type == 'pph_badan':
                result = calc.pph_badan(
                    float(data.get('profit', 0)),
                    float(data.get('omzet', 0)),
                )
            else:
                return jsonify({'error': f'Unknown type: {calc_type}'}), 400
            return jsonify({'success': True, 'result': result})
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    return app


# ─── Entry point ───
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    print('=' * 55)
    print('  Corporate Tax Manager — Web App')
    print(f'  Buka http://localhost:{port} di browser')
    print('=' * 55)
    app.run(host='0.0.0.0', port=port, debug=debug)
