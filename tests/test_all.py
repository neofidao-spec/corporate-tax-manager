"""
Test Suite — Corporate Tax Manager
Unit tests untuk tax_calculator dan integration test untuk web_app.
"""

import os
import sys
import json
import unittest
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.tax_calculator import TaxCalculator
from data.tax_db import TaxDB


class TestTaxCalculator(unittest.TestCase):
    """Unit tests for all tax calculation functions."""

    def setUp(self):
        self.calc = TaxCalculator()

    # ─── Helper assertions ───

    def assertResult(self, result, expected_fields):
        for key, expected_type in expected_fields.items():
            self.assertIn(key, result, f"Missing field: {key}")
            if expected_type == 'float':
                self.assertIsInstance(result[key], (int, float),
                                       f"{key} should be numeric")
            elif expected_type == 'str':
                self.assertIsInstance(result[key], str,
                                       f"{key} should be string")

    def assertResultValues(self, result, **kwargs):
        for key, expected in kwargs.items():
            actual = result.get(key)
            if isinstance(expected, float):
                self.assertAlmostEqual(actual, expected, delta=abs(expected)*0.001
                                        if expected != 0 else 0.01,
                                        msg=f"{key}: expected {expected}, got {actual}")
            else:
                self.assertEqual(actual, expected,
                                 f"{key}: expected {expected}, got {actual}")

    # ─── PPh 21 Tests ───

    def test_pph21_pegawai_rendah(self):
        """Pegawai dengan gaji di bawah PTKP harus 0."""
        r = self.calc.pph21(3_500_000, 'K3')
        self.assertEqual(r['pph_monthly'], 0.0)
        self.assertEqual(r['pph_yearly'], 0.0)

    def test_pph21_pegawai_normal(self):
        """Gaji 15jt TK2 harus menghasilkan PPh positif."""
        r = self.calc.pph21(15_000_000, 'TK2')
        self.assertGreater(r['pph_monthly'], 0)
        self.assertGreater(r['pph_yearly'], 0)
        self.assertResultValues(r, ptkp=63_000_000)
        self.assertIn('metode', r)

    def test_pph21_pegawai_tinggi(self):
        """Gaji tinggi, tarif progresif 30%."""
        r = self.calc.pph21(500_000_000, 'TK0')
        self.assertGreater(r['pph_monthly'], 0)
        # PPh setahun harus signifikan
        self.assertGreater(r['pph_yearly'], 500_000_000 * 0.25)

    def test_pph21_take_home_pay(self):
        """Take home pay = gaji - PPh 21."""
        r = self.calc.pph21(10_000_000, 'K1')
        self.assertAlmostEqual(r['take_home_pay'],
                                r['gross_monthly'] - r['pph_monthly'], delta=0.01)

    def test_pph21_validation_negative(self):
        with self.assertRaises(ValueError):
            self.calc.pph21(-1000, 'TK0')

    def test_pph21_validation_str(self):
        with self.assertRaises(ValueError):
            self.calc.pph21("abc", 'TK0')

    def test_pph21_non_pegawai(self):
        r = self.calc.pph21_non_pegawai(20_000_000, 'TK0')
        self.assertResultValues(r, gross_income=20_000_000)
        self.assertIn('metode', r)
        # 50% norma: neto year = 20jt * 0.5 * 12 = 120jt; PKP = 120jt - 54jt = 66jt
        self.assertResultValues(r, net_yearly=120_000_000, pkp=66_000_000)

    def test_pph21_invalid_status(self):
        with self.assertRaises(ValueError):
            self.calc.pph21(10_000_000, 'INVALID')

    def test_pph23_case_insensitive_type(self):
        r = self.calc.pph23(50_000_000, 'dividen')
        self.assertResultValues(r, pph=7_500_000, tarif='15%', jenis='Dividen')

    def test_db_rejects_negative_withholding(self):
        import tempfile, os
        path = tempfile.mktemp(suffix='.db')
        try:
            db = TaxDB(path)
            db.init_tables()
            with self.assertRaises(ValueError):
                db.add_withholding('V', -1000, 'Jasa', 'pph23', '2%')
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_delete_withholding_requires_post(self):
        from web_app import create_app
        app = create_app(testing=True)
        client = app.test_client()
        r = client.get('/withholding/delete/1')
        self.assertEqual(r.status_code, 405)

    # ─── PPh 23 Tests ───

    def test_pph23_jasa(self):
        r = self.calc.pph23(50_000_000, 'Jasa')
        self.assertResultValues(r, pph=1_000_000, tarif='2%')

    def test_pph23_dividen(self):
        r = self.calc.pph23(100_000_000, 'Dividen')
        self.assertResultValues(r, pph=15_000_000, tarif='15%')

    def test_pph23_edge_zero(self):
        r = self.calc.pph23(0, 'Jasa')
        self.assertResultValues(r, pph=0, diterima=0)

    def test_pph23_edge_large(self):
        r = self.calc.pph23(10_000_000_000, 'Royalti')
        self.assertResultValues(r, pph=1_500_000_000)

    def test_pph23_invalid_type_default_to_jasa(self):
        r = self.calc.pph23(50_000_000, 'Unknown')
        # Unknown maps to default 2%
        self.assertResultValues(r, pph=1_000_000, tarif='2%')

    # ─── PPh 26 Tests ───

    def test_pph26_standard(self):
        r = self.calc.pph26(100_000_000, 'Jasa')
        self.assertResultValues(r, pph=20_000_000, tarif='20%',
                                jenis_pajak='PPh 26')

    def test_pph26_with_npwp(self):
        r = self.calc.pph26(100_000_000, 'Jasa', have_npwp=True)
        self.assertResultValues(r, pph=2_000_000, tarif='2%',
                                jenis_pajak='PPh 23 (LN dgn NPWP)')

    # ─── PPN Tests ───

    def test_ppn_standard(self):
        r = self.calc.ppn(20_000_000, 11)
        self.assertResultValues(r, dpp=20_000_000, ppn=2_200_000,
                                total=22_200_000, tarif='11%')

    def test_ppn_include(self):
        r = self.calc.ppn(22_200_000, 11, include_ppn=True)
        self.assertAlmostEqual(r['dpp'], 20_000_000, delta=10)
        self.assertAlmostEqual(r['ppn'], 2_200_000, delta=10)

    def test_ppn_various_tariffs(self):
        for tarif in [11, 12]:
            r = self.calc.ppn(10_000_000, tarif)
            expected_ppn = 10_000_000 * tarif / 100
            self.assertResultValues(r, ppn=expected_ppn)

    def test_ppn_impor(self):
        r = self.calc.ppn_impor(100_000_000, 5_000_000)
        self.assertResultValues(r, dpp=105_000_000,
                                ppn=105_000_000 * 0.11)

    # ─── PPh Badan Tests ───

    def test_pph_badan_pp23(self):
        """Omzet <= 4.8M → PP 23: 0.5%."""
        r = self.calc.pph_badan(100_000_000, 3_000_000_000)
        self.assertResultValues(r, pph=15_000_000)
        self.assertIn('PP 23', r['metode'])

    def test_pph_badan_31e(self):
        """Omzet <= 50M → Pasal 31E."""
        r = self.calc.pph_badan(5_000_000_000, 30_000_000_000)
        self.assertIn('31E', r['metode'])
        self.assertGreater(r['pph'], 0)

    def test_pph_badan_normal(self):
        """Omzet > 50M → Pasal 17: 22%."""
        r = self.calc.pph_badan(10_000_000_000, 100_000_000_000)
        self.assertResultValues(r, pph=2_200_000_000)
        self.assertIn('22%', r['metode'])

    # ─── PPh Final Tests ───

    def test_final_sewa_tanah(self):
        r = self.calc.pph_final_sewa_tanah(200_000_000)
        self.assertResultValues(r, pph=20_000_000, tarif='10%')

    def test_final_konstruksi_kecil(self):
        r = self.calc.pph_final_konstruksi(1_000_000_000, 'kecil')
        self.assertResultValues(r, pph=20_000_000, tarif='2%')

    def test_final_konstruksi_menengah(self):
        r = self.calc.pph_final_konstruksi(1_000_000_000, 'menengah')
        self.assertResultValues(r, pph=30_000_000, tarif='3%')

    def test_final_konstruksi_lainnya(self):
        r = self.calc.pph_final_konstruksi(1_000_000_000, 'lainnya')
        self.assertResultValues(r, pph=40_000_000, tarif='4%')

    def test_final_pesangon(self):
        r = self.calc.pph_final_pesangon(300_000_000)
        # 0-50jt: 0%, 50-100jt: 5%=2.5jt, 100-300jt: 15%=30jt → 32.5jt total
        self.assertResultValues(r, pph=32_500_000)

    def test_final_pesangon_rendah(self):
        r = self.calc.pph_final_pesangon(40_000_000)
        self.assertResultValues(r, pph=0)

    def test_final_penjualan_tanah(self):
        r = self.calc.pph_final_penjualan_tanah(1_000_000_000)
        self.assertResultValues(r, pph=25_000_000, tarif='2.5%')
        self.assertIn('ppn', r)

    def test_final_bunga_deposito(self):
        r = self.calc.pph_final_bunga_deposito(10_000_000)
        self.assertResultValues(r, pph=2_000_000, tarif='20%', diterima=8_000_000)

    def test_pph22_impor(self):
        r = self.calc.pph22_impor(500_000_000, have_api=True)
        self.assertResultValues(r, pph=12_500_000, tarif='2.5%')

    def test_pph22_impor_no_api(self):
        r = self.calc.pph22_impor(500_000_000, have_api=False)
        self.assertResultValues(r, pph=37_500_000, tarif='7.5%')

    # ─── Validation Tests ───

    def test_validation_negative_values(self):
        for func, args in [
            (self.calc.pph21, (-1000, 'TK0')),
            (self.calc.pph23, (-1000, 'Jasa')),
            (self.calc.ppn, (-1000, 11)),
            (self.calc.pph_badan, (-1000, 1000)),
            (self.calc.pph_final_sewa_tanah, (-1000,)),
        ]:
            with self.subTest(func=func.__name__):
                with self.assertRaises(ValueError):
                    func(*args)

    def test_validation_zero_values(self):
        # Zero should be accepted and produce zero tax
        for func, args, expected_key in [
            (self.calc.pph21, (0, 'TK0'), 'pph_monthly'),
            (self.calc.pph23, (0, 'Jasa'), 'pph'),
            (self.calc.ppn, (0, 11), 'ppn'),
            (self.calc.pph_badan, (0, 0), 'pph'),
        ]:
            with self.subTest(func=func.__name__):
                r = func(*args)
                self.assertEqual(r[expected_key], 0.0)

    def test_validation_invalid_strings(self):
        with self.assertRaises(ValueError):
            self.calc.pph21("not_a_number", 'TK0')
        with self.assertRaises(ValueError):
            self.calc.pph23("abc", 'Jasa')


class TestTaxDB(unittest.TestCase):
    """Integration tests for database layer."""
    TEST_DB = '/data/data/com.termux/files/home/test_corporate_tax.db'

    def setUp(self):
        self.db = TaxDB(self.TEST_DB)
        self.db.init_tables()

    def tearDown(self):
        import os
        if os.path.exists(self.TEST_DB):
            os.remove(self.TEST_DB)

    def test_add_withholding(self):
        rid = self.db.add_withholding("PT ABC", 100_000_000, "Jasa", "pph23", "2%")
        self.assertIsInstance(rid, int)
        self.assertGreater(rid, 0)

    def test_get_all_withholding(self):
        self.db.add_withholding("PT A", 50_000_000, "Jasa", "pph23", "2%")
        self.db.add_withholding("PT B", 25_000_000, "Dividen", "pph23", "15%")
        rows, total = self.db.get_all_withholding()
        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 2)

    def test_add_document(self):
        did = self.db.add_document("Test Doc", "Faktur Pajak", "Lengkap", 2026, 7)
        self.assertIsInstance(did, int)

    def test_get_dashboard_data(self):
        self.db.add_withholding("PT ABC", 100_000_000, "Jasa", "pph23", "2%")
        data = self.db.get_dashboard_data()
        self.assertIn('total_due_this_month', data)
        self.assertIn('doc_count', data)
        self.assertGreater(data['total_due_this_month'], 0)

    def test_get_upcoming_deadlines(self):
        deadlines = self.db.get_upcoming_deadlines()
        self.assertGreater(len(deadlines), 0)
        for d in deadlines:
            self.assertIn('title', d)
            self.assertIn('date', d)
            self.assertIn('status', d)


class TestWebApp(unittest.TestCase):
    """Integration tests for Flask web application."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from web_app import create_app
        cls.app = create_app(testing=True)
        cls.client = cls.app.test_client()

    def test_home_page(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Corporate Tax', r.data)

    def test_calculator_page(self):
        r = self.client.get('/calculator')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Kalkulator', r.data)

    def test_calculator_pph21_post(self):
        r = self.client.post('/calculator', data={
            'calc_type': 'pph21', 'gross': 15000000, 'ptkp_status': 'TK2',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'PPh 21 per Bulan', r.data)

    def test_calculator_pph23_post(self):
        r = self.client.post('/calculator', data={
            'calc_type': 'pph23', 'amount': 50000000, 'obj_type': 'Jasa',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'1.000.000', r.data)

    def test_calculator_final_penjualan_post(self):
        r = self.client.post('/calculator', data={
            'calc_type': 'pph_final_penjualan', 'harga_jual': 1000000000,
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'2.5%', r.data)
        # Locale-independent: comma or dot thousand separators
        self.assertTrue(b'25,000,000' in r.data or b'25.000.000' in r.data)

    def test_calculator_final_bunga_post(self):
        r = self.client.post('/calculator', data={
            'calc_type': 'pph_final_bunga', 'bunga_deposito': 10000000,
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'20%', r.data)
        self.assertTrue(b'2,000,000' in r.data or b'2.000.000' in r.data)

    def test_withholding_page(self):
        r = self.client.get('/withholding')
        self.assertEqual(r.status_code, 200)

    def test_documents_page(self):
        r = self.client.get('/documents')
        self.assertEqual(r.status_code, 200)

    def test_calendar_page(self):
        r = self.client.get('/calendar')
        self.assertEqual(r.status_code, 200)

    def test_api_dashboard(self):
        r = self.client.get('/api/dashboard')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('total_due_this_month', data)

    def test_api_calculate(self):
        r = self.client.post('/api/calculate', json={
            'type': 'pph23', 'amount': 100000000, 'obj_type': 'Jasa',
        })
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data['success'])
        self.assertAlmostEqual(data['result']['pph'], 2_000_000.0)

    def test_api_calculate_invalid(self):
        r = self.client.post('/api/calculate', json={'type': 'unknown'})
        self.assertEqual(r.status_code, 400)

    def test_withholding_crud(self):
        """Full CRUD cycle for withholding records."""
        self.client.post('/withholding/add', data={
            'vendor': 'TestCo', 'amount': 50000000, 'obj_type': 'Jasa',
            'tax_code': 'pph23', 'tariff': '2%', 'description': 'Test',
        }, follow_redirects=True)
        r = self.client.get('/withholding/export')
        lines = r.data.decode().strip().split('\n')
        self.assertGreater(len(lines), 1)

    def test_document_search_and_status_update(self):
        path = '/data/data/com.termux/files/home/test_corporate_tax_docs.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            did = db.add_document('Faktur ABC', 'Faktur Pajak', 'Kurang', 2026, 7, 'catatan uji')
            rows, total = db.get_all_documents(q='ABC')
            self.assertEqual(total, 1)
            self.assertEqual(rows[0]['id'], did)
            ok = db.update_document_status(did, 'Lengkap')
            self.assertTrue(ok)
            rows, _ = db.get_all_documents(status_filter='Lengkap')
            self.assertEqual(rows[0]['status'], 'Lengkap')
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_dashboard_period_selector(self):
        r = self.client.get('/?year=2025&month=3')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'2025', r.data)

    def test_print_withholding_preview(self):
        r = self.client.get('/withholding/print')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Laporan Potongan PPh', r.data)

    def test_document_full_edit(self):
        path = '/data/data/com.termux/files/home/test_corporate_tax_docs_edit.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            did = db.add_document('Judul Lama', 'Faktur Pajak', 'Kurang', 2026, 1, 'n1')
            ok = db.update_document(
                did, title='Judul Baru', category='SPT Masa', status='Lengkap',
                tax_year=2026, tax_month=2, notes='n2',
            )
            self.assertTrue(ok)
            doc = db.get_document(did)
            self.assertIsNotNone(doc)
            self.assertEqual(doc['title'], 'Judul Baru')
            self.assertEqual(doc['category'], 'SPT Masa')
            self.assertEqual(doc['status'], 'Lengkap')
            self.assertEqual(doc['tax_month'], 2)
            self.assertEqual(doc['notes'], 'n2')
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_dashboard_comparison_present(self):
        r = self.client.get('/?year=2026&month=7')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'vs', r.data)

    def test_print_filter_summary(self):
        r = self.client.get('/withholding/print?year=2026&month=3&tax_code=pph23')
        self.assertEqual(r.status_code, 200)
        body = r.data
        self.assertIn(b'Tahun 2026', body)
        self.assertIn(b'PPh 23', body)

    def test_calendar_reminder_crud(self):
        path = '/data/data/com.termux/files/home/test_corporate_tax_reminders.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            rid = db.add_reminder('Deadline Uji', 12, 'desc', 'custom', True, True)
            self.assertGreater(rid, 0)
            m = db.get_calendar_deadlines_map()
            self.assertIn(12, m)
            ok = db.update_reminder(rid, 'Deadline Update', 18, 'd2', 'custom2', True, True)
            self.assertTrue(ok)
            rem = db.get_reminder(rid)
            self.assertIsNotNone(rem)
            assert rem is not None
            self.assertEqual(rem['title'], 'Deadline Update')
            self.assertEqual(str(rem['deadline_date']), '18')
            ok = db.delete_reminder(rid)
            self.assertTrue(ok)
            self.assertIsNone(db.get_reminder(rid))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_calendar_add_reminder_route(self):
        r = self.client.post('/calendar/reminders/add', data={
            'title': 'Custom Route Deadline',
            'deadline_day': 25,
            'description': 'via route',
            'tax_code': 'custom',
            'is_active': 'on',
            'is_recurring': 'on',
            'year': 2026,
            'month': 7,
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Custom Route Deadline', r.data)
        r2 = self.client.get('/calendar')
        self.assertEqual(r2.status_code, 200)
        self.assertIn(b'Custom Route Deadline', r2.data)

    def test_one_time_deadline(self):
        path = '/data/data/com.termux/files/home/test_corporate_tax_onetime.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            rid = db.add_reminder(
                'SPT Tahunan Sekali',
                description='sekali',
                tax_code='annual',
                is_recurring=False,
                is_active=True,
                one_time_date='2026-04-30',
            )
            self.assertGreater(rid, 0)
            m = db.get_calendar_deadlines_map(year=2026, month=4)
            self.assertIn(30, m)
            m2 = db.get_calendar_deadlines_map(year=2026, month=5)
            self.assertNotIn(30, m2)
            # invalid formats
            with self.assertRaises(ValueError):
                db.add_reminder('X', is_recurring=False, one_time_date='30-04-2026')
            with self.assertRaises(ValueError):
                db.add_reminder('Y', is_recurring=True, deadline_day=0)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_pph21_log_page(self):
        r = self.client.get('/pph21')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Log PPh 21', r.data)

    def test_pph21_log_crud(self):
        r = self.client.post('/pph21/add', data={
            'employee_name': 'Budi Uji',
            'gross_salary': 15000000,
            'ptkp_status': 'TK2',
            'year': 2026,
            'month': 7,
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Budi Uji', r.data)
        # search
        r2 = self.client.get('/pph21?q=Budi')
        self.assertEqual(r2.status_code, 200)
        self.assertIn(b'Budi Uji', r2.data)
        # DB helpers
        path = '/data/data/com.termux/files/home/test_corporate_tax_pph21.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            rid = db.add_pph21('Ani', 10000000, 1, 'K1', 500000, 2026, 7)
            rows, total = db.get_pph21_log(q='Ani')
            self.assertEqual(total, 1)
            self.assertEqual(rows[0]['id'], rid)
            self.assertGreater(db.get_total_pph21(2026), 0)
            self.assertTrue(db.delete_pph21(rid))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_pph21_export_csv(self):
        self.client.post('/pph21/add', data={
            'employee_name': 'Export Pegawai',
            'gross_salary': 10000000,
            'ptkp_status': 'TK0',
            'year': 2026,
            'month': 7,
        }, follow_redirects=True)
        r = self.client.get('/pph21/export?year=2026')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'text/csv', r.content_type.encode() if isinstance(r.content_type, str) else r.headers.get('Content-Type', '').encode())
        self.assertIn(b'Export Pegawai', r.data)

    def test_pph21_print_preview(self):
        self.client.post('/pph21/add', data={
            'employee_name': 'Print Pegawai',
            'gross_salary': 12000000,
            'ptkp_status': 'K1',
            'year': 2026,
            'month': 7,
        }, follow_redirects=True)
        r = self.client.get('/pph21/print?year=2026&month=7')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Laporan Log PPh 21', r.data)
        self.assertIn(b'Print Pegawai', r.data)
        self.assertIn(b'window.print', r.data)

    def test_period_report_page(self):
        r = self.client.get('/reports/period?year=2026&month=7')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Laporan periode', r.data)

    def test_period_report_print_and_export(self):
        # seed some data for current period
        self.client.post('/withholding/add', data={
            'vendor': 'Print Vendor', 'amount': 100000000, 'obj_type': 'Jasa',
            'tax_code': 'pph23', 'tariff': '2%', 'description': 'seed',
        }, follow_redirects=True)
        r = self.client.get('/reports/period/print?year=2026&month=7')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Laporan Pajak Periode', r.data)
        self.assertIn(b'window.print', r.data)

        r2 = self.client.get('/reports/period/export?year=2026&month=7')
        self.assertEqual(r2.status_code, 200)
        ctype = r2.headers.get('Content-Type', '')
        self.assertIn('text/csv', ctype)
        self.assertIn(b'TOTAL', r2.data)
        self.assertIn(b'Kode Pajak', r2.data)

    def test_summary_by_period_includes_pph21(self):
        path = '/data/data/com.termux/files/home/test_corporate_tax_summary.db'
        try:
            if os.path.exists(path):
                os.remove(path)
            db = TaxDB(path)
            db.init_tables()
            db.add_withholding('Vendor A', 100000000, 'Jasa', 'pph23', '2%', 'x')
            db.add_pph21('Pegawai A', 15000000, 0, 'TK0', 500000, 2026, 7)
            # Force period fields if add_withholding uses now
            # re-read via summary using current year/month of inserted rows
            rows, _ = db.get_all_withholding(limit=1)
            year = rows[0]['tax_year']
            month = rows[0]['tax_month']
            # also insert pph21 for same period
            db.add_pph21('Pegawai B', 10000000, 0, 'TK0', 400000, year, month)
            s = db.get_summary_by_period(year, month)
            self.assertGreaterEqual(s['grand_total'], 500000)
            codes = {d['tax_code'] for d in s['details']}
            self.assertIn('pph23', codes)
            self.assertIn('pph21', codes)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_calculator_summary_helper(self):
        from data.tax_calculator import TaxCalculator
        calc = TaxCalculator()
        r = calc.pph23(50_000_000, 'Jasa')
        text = calc.summary(r)
        self.assertIn('Pph', text)
        self.assertIn('Rp', text)

    def test_dashboard_quick_actions(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'/pph21', r.data)
        self.assertIn(b'/reports/period', r.data)
        self.assertIn(b'/documents', r.data)
        self.assertIn(b'/calendar', r.data)

    def test_empty_state_and_urgent_reminder(self):
        # Empty pages still render consistent empty-state markup
        for path, marker in [
            ('/withholding', b'empty-title'),
            ('/documents', b'empty-title'),
            ('/pph21', b'empty-title'),
            ('/reports/period', b'empty-title'),
        ]:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn(b'empty-state', r.data, path)
            self.assertIn(marker, r.data, path)

        # Seed an urgent one-time deadline for today → dashboard banner
        r = self.client.post('/calendar/reminders/add', data={
            'title': 'Deadline Urgent UI',
            'one_time_date': date.today().isoformat(),
            'description': 'urgent',
            'tax_code': 'custom',
            # is_recurring unchecked
            'is_active': 'on',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        dash = self.client.get('/')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'Reminder deadline', dash.data)
        self.assertIn(b'Deadline Urgent UI', dash.data)

    def test_density_toggle_and_skeleton_markup(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'densityToggle', r.data)
        self.assertIn(b'pageSkeleton', r.data)
        self.assertIn(b'density-compact', r.data)
        self.assertIn(b'is-loading', r.data)
        self.assertIn(b'ctm_density', r.data)
        self.assertIn(b'app-content-ready', r.data)
        self.assertIn(b'v1.1.2', r.data)

    def test_accessibility_landmarks(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'skip-link', r.data)
        self.assertIn(b'Loncat ke konten utama', r.data)
        self.assertIn(b'id="main-content"', r.data)
        self.assertIn(b'aria-label="Navigasi utama"', r.data)
        self.assertIn(b'aria-current="page"', r.data)
        self.assertIn(b'aria-busy="true"', r.data)
        self.assertIn(b'prefers-reduced-motion', r.data)
        # active home page should mark beranda as current
        self.assertIn(b'aria-current="page"', r.data)

    def test_contrast_status_tokens(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        # darker text tokens for soft-bg badges/alerts
        self.assertIn(b'--success-text', r.data)
        self.assertIn(b'--warning-text', r.data)
        self.assertIn(b'--danger-text', r.data)
        self.assertIn(b'--info-text', r.data)
        self.assertIn(b'status-chip', r.data)
        self.assertIn(b'.status-chip.overdue', r.data)
        self.assertIn(b'.status-chip.soon', r.data)
        self.assertIn(b'.status-chip.ok', r.data)

    def test_android_prefs_helpers(self):
        from data.app_prefs import APP_VERSION, load_prefs, save_prefs, prefs_path
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as td:
            path = prefs_path(user_data_dir=td)
            self.assertEqual(load_prefs(path=path), {})
            self.assertTrue(save_prefs({'compact': True}, path=path))
            self.assertTrue(load_prefs(path=path).get('compact'))
            self.assertTrue(save_prefs({'compact': False}, path=path))
            self.assertFalse(load_prefs(path=path).get('compact'))
            # corrupt file falls back to empty dict
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{not-json')
            self.assertEqual(load_prefs(path=path), {})
            # missing parent handled
            nested = os.path.join(td, 'nested', 'ctm_prefs.json')
            self.assertTrue(save_prefs({'x': 1}, path=nested))
            self.assertEqual(load_prefs(path=nested).get('x'), 1)
        self.assertEqual(APP_VERSION, '1.1.2')

    def test_export_utils_pph21_csv(self):
        from data.export_utils import (
            pph21_csv_rows, render_csv, export_pph21_csv, default_export_filename,
            withholding_csv_rows, export_withholding_csv,
            period_report_csv_rows, export_period_report_csv,
        )
        import tempfile
        import os
        sample = [{
            'id': 1,
            'employee_name': 'Budi',
            'gross_salary': 15000000,
            'dependents': 0,
            'ptkp_status': 'TK0',
            'pph21_amount': 250000,
            'period_year': 2026,
            'period_month': 7,
            'created_at': '2026-07-22',
        }]
        rows = pph21_csv_rows(sample)
        self.assertEqual(rows[0][0], 'ID')
        self.assertEqual(rows[1][1], 'Budi')
        csv_text = render_csv(rows)
        self.assertIn('Budi', csv_text)
        self.assertIn('250000', csv_text)
        with tempfile.TemporaryDirectory() as td:
            path, count, total = export_pph21_csv(sample, td)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(count, 1)
            self.assertEqual(total, 250000.0)
            self.assertTrue(path.endswith('.csv'))
        self.assertTrue(default_export_filename('pph21_export').startswith('pph21_export_'))

        wh = [{
            'id': 9, 'vendor': 'PT ABC', 'amount': 1000000, 'obj_type': 'Jasa',
            'tax_code': 'pph23', 'tariff_label': '2%', 'pph_amount': 20000,
            'description': 'konsultan', 'created_at': '2026-07-22',
            'tax_year': 2026, 'tax_month': 7,
        }]
        wh_rows = withholding_csv_rows(wh)
        self.assertEqual(wh_rows[1][1], 'PT ABC')
        with tempfile.TemporaryDirectory() as td:
            path, count, total = export_withholding_csv(wh, td)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(count, 1)
            self.assertEqual(total, 20000.0)

        summary = {
            'details': [{
                'tax_code': 'pph23', 'obj_type': 'Jasa', 'count': 2,
                'total_amount': 2000000, 'total_tax': 40000,
            }],
            'transaction_count': 2,
            'grand_total': 40000,
        }
        pr_rows = period_report_csv_rows(summary, 2026, 7)
        self.assertIn('TOTAL', pr_rows[-1])
        with tempfile.TemporaryDirectory() as td:
            path, count, total = export_period_report_csv(summary, 2026, 7, td)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(count, 1)
            self.assertEqual(total, 40000.0)
            self.assertIn('laporan_periode_2026_07.csv', path)

        # Web export still works via shared helpers
        for path in ('/pph21/export', '/withholding/export', '/reports/period/export?year=2026&month=7'):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn('text/csv', r.content_type, path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
