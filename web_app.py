"""
Corporate Tax Manager — Flask Web App
Akses via browser: http://localhost:5000
"""
import os, sys, sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask import g

app = Flask(__name__)
app.secret_key = 'corporate-tax-manager-secret-key'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'tax_data.db')


# ─── Database ───
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS withholding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            amount REAL NOT NULL,
            obj_type TEXT NOT NULL,
            tariff_label TEXT DEFAULT '2%',
            pph_amount REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            tax_year INTEGER NOT NULL DEFAULT (CAST(strftime('%Y', 'now') AS INTEGER)),
            tax_month INTEGER NOT NULL DEFAULT (CAST(strftime('%m', 'now') AS INTEGER))
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Umum',
            status TEXT NOT NULL DEFAULT 'Lengkap',
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.commit()
    conn.close()


# ─── Tax Calculator ───
def calc_pph21(gross_monthly, dependents=0):
    dependents = min(dependents, 3)
    ptkp = 54_000_000 + (4_500_000 * dependents)
    biaya_jabatan = min(gross_monthly * 0.05 * 12, 6_000_000)
    iuran_pensiun = min(gross_monthly * 0.01 * 12, 2_400_000)
    net_year = (gross_monthly * 12) - biaya_jabatan - iuran_pensiun
    pkp = max(0, net_year - ptkp)

    lapisan = [
        (0, 60_000_000, 0.05),
        (60_000_000, 250_000_000, 0.15),
        (250_000_000, 500_000_000, 0.25),
        (500_000_000, 5_000_000_000, 0.30),
        (5_000_000_000, float('inf'), 0.35),
    ]
    pph_year = 0
    remaining = pkp
    for lower, upper, rate in lapisan:
        if remaining <= 0:
            break
        bracket = min(remaining, upper - lower)
        pph_year += bracket * rate
        remaining -= bracket
    return {
        'pph_monthly': round(pph_year / 12, 2),
        'net_monthly': round(gross_monthly, 2),
        'ptkp': round(ptkp, 2),
        'pkp': round(pkp, 2),
        'pph_yearly': round(pph_year, 2),
    }

def calc_pph23(amount, obj_type='Jasa'):
    tariffs = {'Dividen': 0.15, 'Bunga': 0.15, 'Royalti': 0.15,
               'Jasa': 0.02, 'Sewa': 0.02, 'Hadiah': 0.15}
    rate = tariffs.get(obj_type.title(), 0.02)
    pph = amount * rate
    return {'pph': round(pph, 2), 'net': round(amount - pph, 2), 'rate': rate}

def calc_ppn(price, tariff=11):
    ppn = price * (tariff / 100)
    return {'ppn': round(ppn, 2), 'total': round(price + ppn, 2), 'tariff': tariff}

def calc_pph_badan(profit, omzet):
    if omzet <= 4_800_000_000:
        return {'pph': round(omzet * 0.005, 2), 'method': 'PP 23 (0.5% dari omzet)'}
    if omzet <= 50_000_000_000:
        fasilitas_pkp = (4_800_000_000 / omzet) * profit
        non_fasilitas = profit - fasilitas_pkp
        pph = (fasilitas_pkp * 0.11) + (non_fasilitas * 0.22)
        return {'pph': round(pph, 2), 'method': 'Pasal 31E (fasilitas 50%)'}
    else:
        return {'pph': round(profit * 0.22, 2), 'method': 'Pasal 17 (22%)'}


# ─── Routes ───
@app.route('/')
def index():
    db = get_db()
    now = datetime.now()
    year, month = now.year, now.month

    pph23_total = db.execute(
        "SELECT COALESCE(SUM(pph_amount),0) FROM withholding WHERE tax_year=? AND tax_month=?",
        (year, month)).fetchone()[0]

    docs_total = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    records_count = db.execute("SELECT COUNT(*) FROM withholding").fetchone()[0]

    # Deadlines
    today = date.today()
    deadlines = []
    for y, m, d, title in [
        (year, month, 10, 'SPT Masa PPN'),
        (year, month, 20, 'PPh 21 Masa'),
        (year, month, 20, 'PPh 23/26 Masa'),
    ]:
        dl = date(y, m, d)
        diff = (dl - today).days
        deadlines.append({'title': title, 'date': dl.strftime('%d %b %Y'),
                          'status': 'LEWAT' if diff < 0 else 'SEGERA' if diff <= 7 else 'OK'})

    return render_template('index.html', pph23_total=pph23_total,
                           docs_total=docs_total, records_count=records_count,
                           deadlines=deadlines, year=year, month=month)


@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    result = None
    calc_type = request.form.get('calc_type', 'pph21')
    if request.method == 'POST':
        try:
            if calc_type == 'pph21':
                gross = float(request.form.get('gross', 0))
                dep = int(request.form.get('dependents', 0))
                result = calc_pph21(gross, dep)
            elif calc_type == 'pph23':
                amt = float(request.form.get('amount', 0))
                obj = request.form.get('obj_type', 'Jasa')
                result = calc_pph23(amt, obj)
            elif calc_type == 'ppn':
                price = float(request.form.get('price', 0))
                tarif = float(request.form.get('tariff', 11))
                result = calc_ppn(price, tarif)
            elif calc_type == 'pph_badan':
                profit = float(request.form.get('profit', 0))
                omzet = float(request.form.get('omzet', 0))
                result = calc_pph_badan(profit, omzet)
        except (ValueError, TypeError):
            flash('Masukkan angka yang valid!', 'error')
    return render_template('calculator.html', result=result, calc_type=calc_type)


@app.route('/withholding')
def withholding():
    db = get_db()
    records = db.execute(
        "SELECT * FROM withholding ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    return render_template('withholding.html', records=records)

@app.route('/withholding/add', methods=['POST'])
def add_withholding():
    db = get_db()
    vendor = request.form['vendor']
    amount = float(request.form.get('amount', 0))
    obj_type = request.form['obj_type']
    tariff_label = request.form.get('tariff', '2%')

    tariff_map = {'2%': 0.02, '15%': 0.15, '20%': 0.20}
    tariff = tariff_map.get(tariff_label, 0.02)
    pph = amount * tariff

    db.execute(
        "INSERT INTO withholding (vendor, amount, obj_type, tariff_label, pph_amount) VALUES (?,?,?,?,?)",
        (vendor, amount, obj_type, tariff_label, pph))
    db.commit()
    flash(f'Potongan PPh {obj_type} Rp {pph:,.0f} berhasil dicatat!', 'success')
    return redirect(url_for('withholding'))

@app.route('/withholding/delete/<int:rid>')
def delete_withholding(rid):
    db = get_db()
    db.execute("DELETE FROM withholding WHERE id=?", (rid,))
    db.commit()
    flash('Data potongan berhasil dihapus.', 'success')
    return redirect(url_for('withholding'))


@app.route('/documents')
def documents():
    db = get_db()
    docs = db.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template('documents.html', docs=docs)

@app.route('/documents/add', methods=['POST'])
def add_document():
    db = get_db()
    db.execute(
        "INSERT INTO documents (title, category, status) VALUES (?,?,?)",
        (request.form['title'], request.form.get('category', 'Umum'), request.form.get('status', 'Lengkap')))
    db.commit()
    flash('Dokumen berhasil dicatat!', 'success')
    return redirect(url_for('documents'))

@app.route('/documents/delete/<int:did>')
def delete_document(did):
    db = get_db()
    db.execute("DELETE FROM documents WHERE id=?", (did,))
    db.commit()
    flash('Dokumen berhasil dihapus.', 'success')
    return redirect(url_for('documents'))


@app.route('/calendar')
def calendar_view():
    import calendar as cal_mod
    today = date.today()
    y, m = today.year, today.month
    cal = cal_mod.monthcalendar(y, m)
    month_name = cal_mod.month_name[m]
    deadlines_map = {10: 'PPN', 15: 'PPh Final', 20: 'PPh 21/23', 21: 'PPh 26'}
    return render_template('calendar.html', cal=cal, month_name=month_name,
                           year=y, month=m, today=today, deadlines=deadlines_map)


if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("Corporate Tax Manager — Web App")
    print("Buka http://localhost:5000 di browser")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
