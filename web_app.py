"""
Corporate Tax Manager — Web Application
Flask app dengan blueprint architecture.
Membantu tugas bagian pajak perusahaan secara komprehensif.
"""

import os
import sys
import json
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, g, send_file, Response,
)
from io import StringIO
import csv

# Ensure data module is importable
sys.path.insert(0, os.path.dirname(__file__))

from data.tax_calculator import TaxCalculator
from data.tax_db import TaxDB

calc = TaxCalculator()


# ─── App Factory ───
def create_app(testing=False):
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'corporate-tax-mgr-2026')
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
        return {'now': datetime.now(), 'today': date.today()}

    # ══════════════════════════════════════════════════
    # ROUTES: Dashboard
    # ══════════════════════════════════════════════════

    @app.route('/')
    def index():
        data = g.db.get_dashboard_data()
        deadlines = g.db.get_upcoming_deadlines()
        yearly = g.db.get_yearly_summary(data['year'])
        return render_template('index.html', dash=data, deadlines=deadlines,
                               yearly=yearly)

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

                elif calc_type == 'pph22_impor':
                    nilai = float(request.form.get('nilai_p22', 0))
                    api = request.form.get('have_api') == 'on'
                    results = calc.pph22_impor(nilai, api)

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Kesalahan perhitungan: {str(e)}', 'error')

        return render_template('calculator.html', results=results, calc_type=calc_type)

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

        records, total = g.db.get_all_withholding(
            limit=per_page, offset=(page - 1) * per_page,
            year=year, month=month, tax_code=tax_code,
        )
        total_pages = max(1, (total + per_page - 1) // per_page)
        return render_template('withholding.html', records=records,
                               page=page, total_pages=total_pages,
                               total=total, year=year, month=month, tax_code=tax_code)

    @app.route('/withholding/add', methods=['POST'])
    def add_withholding():
        try:
            vendor = request.form.get('vendor', '').strip()
            if not vendor:
                flash('Nama vendor harus diisi', 'error')
                return redirect(url_for('withholding'))
            amount = float(request.form.get('amount', 0))
            obj_type = request.form.get('obj_type', 'Jasa')
            tax_code = request.form.get('tax_code', 'pph23')
            tariff_label = request.form.get('tariff', '2%')
            description = request.form.get('description', '')

            rid = g.db.add_withholding(vendor, amount, obj_type, tax_code, tariff_label, description)
            # Get the result from calculator for display
            if tax_code == 'pph26':
                res = calc.pph26(amount, obj_type)
            else:
                res = calc.pph23(amount, obj_type)

            flash(f'Data tersimpan: {vendor} — Rp {res["pph"]:,.0f}', 'success')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Gagal menyimpan: {str(e)}', 'error')

        return redirect(url_for('withholding'))

    @app.route('/withholding/delete/<int:rid>')
    def delete_withholding(rid):
        g.db.delete_withholding(rid)
        flash('Data dihapus', 'success')
        return redirect(url_for('withholding'))

    @app.route('/withholding/export')
    def export_withholding():
        records, _ = g.db.get_all_withholding(limit=10000)
        output = StringIO()
        w = csv.writer(output)
        w.writerow(['ID', 'Vendor', 'Jumlah Bruto', 'Jenis Objek', 'Jenis Pajak',
                     'Tarif', 'PPh', 'Deskripsi', 'Tgl Input', 'Tahun', 'Bulan'])
        for r in records:
            w.writerow([
                r['id'], r['vendor'], r['amount'], r['obj_type'], r['tax_code'],
                r['tariff_label'], r['pph_amount'], r['description'],
                r['created_at'], r['tax_year'], r['tax_month'],
            ])
        return Response(
            output.getvalue(),
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

        docs, total = g.db.get_all_documents(
            limit=per_page, offset=(page - 1) * per_page,
            category=category, status_filter=status_filter,
        )
        total_pages = max(1, (total + per_page - 1) // per_page)
        return render_template('documents.html', docs=docs, page=page,
                               total_pages=total_pages, total=total,
                               category=category, status_filter=status_filter)

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

    @app.route('/documents/delete/<int:did>')
    def delete_document(did):
        g.db.delete_document(did)
        flash('Dokumen dihapus', 'success')
        return redirect(url_for('documents'))

    # ══════════════════════════════════════════════════
    # ROUTES: Calendar
    # ══════════════════════════════════════════════════

    @app.route('/calendar')
    def calendar_view():
        import calendar as cal_mod
        now = date.today()
        y = request.args.get('year', now.year, type=int)
        m = request.args.get('month', now.month, type=int)

        cal = cal_mod.monthcalendar(y, m)
        month_name = cal_mod.month_name[m]
        deadlines_map = {10: 'PPN', 15: 'PPh Final', 20: 'PPh 21/23', 21: 'PPh 26'}

        # Navigation
        prev_m = m - 1 if m > 1 else 12
        prev_y = y if m > 1 else y - 1
        next_m = m + 1 if m < 12 else 1
        next_y = y if m < 12 else y + 1

        return render_template('calendar.html', cal=cal, month_name=month_name,
                               year=y, month=m, today=now, deadlines=deadlines_map,
                               prev_m=prev_m, prev_y=prev_y, next_m=next_m, next_y=next_y)

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
