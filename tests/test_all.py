"""
Test Suite — Corporate Tax Manager
Unit tests untuk tax_calculator dan integration test untuk web_app.
"""

import os
import sys
import json
import unittest
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
