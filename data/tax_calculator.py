"""
Tax Calculator — Corporate Tax Manager
Perhitungan lengkap PPh 21, 23/26, PPN, PPh Badan, PPh Final (Indonesia)
Validasi input, tarif terbaru, edge case handling.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Union, Optional


def _rupiah(val: float) -> str:
    return f'Rp {val:,.0f}'


def _validate_positive(val, name: str) -> float:
    try:
        v = float(val)
    except (TypeError, ValueError):
        raise ValueError(f'{name} harus berupa angka')
    if v < 0:
        raise ValueError(f'{name} tidak boleh negatif')
    return v


def _validate_int(val, name: str) -> int:
    try:
        v = int(val)
    except (TypeError, ValueError):
        raise ValueError(f'{name} harus berupa bilangan bulat')
    if v < 0:
        raise ValueError(f'{name} tidak boleh negatif')
    return v


class TaxCalculator:
    """Perhitungan Pajak Penghasilan Indonesia.
    Mencakup PPh 21, PPh 23/26, PPN, PPh Badan, PPh Final.
    """

    # ─── PTKP (Penghasilan Tidak Kena Pajak) ───
    PTKP = {
        'TK0': 54_000_000,
        'TK1': 58_500_000,
        'TK2': 63_000_000,
        'TK3': 67_500_000,
        'K0':  58_500_000,
        'K1':  63_000_000,
        'K2':  67_500_000,
        'K3':  72_000_000,
    }

    # Biaya jabatan: 5% x penghasilan bruto, max 500rb/bln = 6jt/thn
    BIAYA_JABATAN_PERSEN = 0.05
    BIAYA_JABATAN_MAX_THN = 6_000_000

    # Iuran pensiun: max 200rb/bln = 2.4jt/thn
    IURAN_PENSIUN_MAX_THN = 2_400_000

    # Tarif PPh 21 Pasal 17 (lapisan terbaru — UU HPP)
    LAPISAN_PPH21 = [
        (0, 60_000_000, 0.05),
        (60_000_000, 250_000_000, 0.15),
        (250_000_000, 500_000_000, 0.25),
        (500_000_000, 5_000_000_000, 0.30),
        (5_000_000_000, float('inf'), 0.35),
    ]

    # Tarif PPh 23
    TARIF_PPH23: Dict[str, float] = {
        'Jasa': 0.02,
        'Sewa': 0.02,
        'Dividen': 0.15,
        'Bunga': 0.15,
        'Royalti': 0.15,
        'Hadiah': 0.15,
    }

    # Tarif PPh 26 (WPLN)
    TARIF_PPH26: Dict[str, float] = {
        'Jasa': 0.20,
        'Sewa': 0.20,
        'Dividen': 0.20,
        'Bunga': 0.20,
        'Royalti': 0.20,
        'Hadiah': 0.20,
    }

    def _pph21_progresif(self, pkp: float) -> float:
        """Hitung PPh dengan tarif progresif Pasal 17."""
        pph = 0.0
        remaining = pkp
        for lower, upper, rate in self.LAPISAN_PPH21:
            if remaining <= 0:
                break
            bracket = min(remaining, upper - lower)
            pph += bracket * rate
            remaining -= bracket
        return pph

    def pph21(self, gross_monthly: float, status: str = 'TK0') -> Dict:
        """
        Hitung PPh 21 masa untuk pegawai tetap.
        status: TK0, TK1, TK2, TK3, K0, K1, K2, K3

        Returns dict berisi seluruh rincian perhitungan.
        """
        gaji = _validate_positive(gross_monthly, 'Gaji bruto')
        status = status.upper()
        ptkp = self.PTKP.get(status, 54_000_000)

        # Biaya jabatan setahun
        biaya_jabatan = min(gaji * self.BIAYA_JABATAN_PERSEN * 12, self.BIAYA_JABATAN_MAX_THN)

        # Iuran pensiun setahun (asumsi 1% dari gaji, max 200rb/bln)
        iuran_pensiun = min(gaji * 0.01 * 12, self.IURAN_PENSIUN_MAX_THN)

        # Penghasilan neto setahun
        neto_year = (gaji * 12) - biaya_jabatan - iuran_pensiun
        pkp = max(0, neto_year - ptkp)
        pph_year = self._pph21_progresif(pkp)
        pph_month = pph_year / 12
        take_home = gaji - pph_month

        return {
            'pph_monthly': round(pph_month, 2),
            'pph_yearly': round(pph_year, 2),
            'gross_monthly': round(gaji, 2),
            'net_yearly': round(neto_year, 2),
            'take_home_pay': round(take_home, 2),
            'ptkp': round(ptkp, 2),
            'pkp': round(pkp, 2),
            'biaya_jabatan': round(biaya_jabatan, 2),
            'iuran_pensiun': round(iuran_pensiun, 2),
            'status': status,
            'metode': 'Tarif Progresif Pasal 17',
        }

    def pph21_non_pegawai(self, gross_income: float, status: str = 'TK0') -> Dict:
        """PPh 21 untuk bukan pegawai (tenaga ahli, komisi, dll)."""
        penghasilan = _validate_positive(gross_income, 'Penghasilan bruto')
        status = status.upper()
        ptkp = self.PTKP.get(status, 54_000_000)

        # 50% penghasilan bruto sebagai penghasilan neto
        neto = penghasilan * 0.50
        neto_year = neto * 12 - min(neto * 12 * self.BIAYA_JABATAN_PERSEN, self.BIAYA_JABATAN_MAX_THN)
        pkp = max(0, neto_year - ptkp)
        pph_year = self._pph21_progresif(pkp)
        pph_month = pph_year / 12

        return {
            'pph_monthly': round(pph_month, 2),
            'pph_yearly': round(pph_year, 2),
            'gross_income': round(penghasilan, 2),
            'pkp': round(pkp, 2),
            'ptkp': round(ptkp, 2),
            'metode': '50% Norma Penghitungan (Bukan Pegawai)',
        }

    # ─── PPh 23 (Wajib Pajak DN) ───
    def pph23(self, amount: float, obj_type: str = 'Jasa') -> Dict:
        """Hitung PPh 23 atas penghasilan WP Dalam Negeri."""
        jumlah = _validate_positive(amount, 'Jumlah bruto')
        obj_type = obj_type.title()
        tariff = self.TARIF_PPH23.get(obj_type, 0.02)
        pph = jumlah * tariff
        diterima = jumlah - pph

        return {
            'pph': round(pph, 2),
            'diterima': round(diterima, 2),
            'tarif': f'{tariff*100:.0f}%',
            'jenis': obj_type,
            'dasar_pengenaan': round(jumlah, 2),
            'jenis_pajak': 'PPh 23',
        }

    # ─── PPh 26 (Wajib Pajak LN) ───
    def pph26(self, amount: float, obj_type: str = 'Jasa', have_npwp: bool = False,
              tax_treaty: bool = False) -> Dict:
        """Hitung PPh 26 untuk Wajib Pajak Luar Negeri."""
        jumlah = _validate_positive(amount, 'Jumlah bruto')
        obj_type = obj_type.title()

        # Jika ada Tax Treaty, tarif mengikuti P3B (default 20% - bisa override user)
        base_tariff = self.TARIF_PPH26.get(obj_type, 0.20)
        tariff = base_tariff

        if have_npwp:
            # WP LN dengan NPWP — tarif PPh 23
            tariff = self.TARIF_PPH23.get(obj_type, 0.02)

        pph = jumlah * tariff
        diterima = jumlah - pph

        return {
            'pph': round(pph, 2),
            'diterima': round(diterima, 2),
            'tarif': f'{tariff*100:.0f}%',
            'jenis': obj_type,
            'dasar_pengenaan': round(jumlah, 2),
            'have_npwp': have_npwp,
            'catatan': 'Tarif P3B (tax treaty) dapat berbeda — konsultasikan dengan KPP' if tax_treaty else '',
            'jenis_pajak': 'PPh 26' if not have_npwp else 'PPh 23 (LN dgn NPWP)',
        }

    # ─── PPN ───
    def ppn(self, price: float, tariff_percent: float = 11, include_ppn: bool = False) -> Dict:
        """
        Hitung PPN.
        include_ppn=True: price sudah termasuk PPN (mencari DPP)
        include_ppn=False: price adalah DPP
        """
        harga = _validate_positive(price, 'Harga')
        tariff = tariff_percent / 100

        if include_ppn:
            # Harga sudah termasuk PPN
            dpp = round(harga / (1 + tariff), 2)
            ppn = round(harga - dpp, 2)
        else:
            dpp = round(harga, 2)
            ppn = round(harga * tariff, 2)

        total = round(dpp + ppn, 2)

        return {
            'dpp': dpp,
            'ppn': ppn,
            'total': total,
            'tarif': f'{tariff_percent:.0f}%',
            'ppn_terutang': ppn,
            'status': 'Harga sudah termasuk PPN' if include_ppn else 'Harga belum termasuk PPN',
        }

    def ppn_impor(self, nilai_impor: float, bea_masuk: float = 0,
                  tariff_percent: float = 11) -> Dict:
        """Hitung PPN atas impor barang."""
        nilai = _validate_positive(nilai_impor, 'Nilai impor')
        bea = _validate_positive(bea_masuk, 'Bea masuk')

        dasar_pengenaan = nilai + bea
        tariff = tariff_percent / 100
        ppn = round(dasar_pengenaan * tariff, 2)

        return {
            'dpp': round(dasar_pengenaan, 2),
            'ppn': ppn,
            'tarif': f'{tariff_percent:.0f}%',
            'bea_masuk': round(bea, 2),
            'nilai_impor': round(nilai, 2),
        }

    # ─── PPh Badan ───
    def pph_badan(self, taxable_profit: float, gross_revenue: float) -> Dict:
        """
        Hitung PPh Badan.
        - PP 23 (UMKM): 0.5% dari omzet (final), untuk omzet <= 4.8M
        - Pasal 31E: fasilitas 50% dari tarif, untuk omzet <= 50M
        - Pasal 17: 22%, untuk omzet > 50M
        """
        laba = _validate_positive(taxable_profit, 'Laba kena pajak')
        omzet = _validate_positive(gross_revenue, 'Omzet')

        if omzet <= 4_800_000_000:
            pph = omzet * 0.005
            metode = 'PP 23 (0.5% dari omzet) — Final'
            tarif_efektif = pph / laba if laba > 0 else 0
            return {
                'pph': round(pph, 2),
                'metode': metode,
                'tarif_efektif': f'{tarif_efektif*100:.1f}%',
                'dpp_omzet': round(omzet, 2),
                'dpp_laba': round(laba, 2),
                'jenis': 'Final (PP 23)',
            }

        if omzet <= 50_000_000_000:
            # Fasilitas Pasal 31E: 50% tarif untuk PKP dari 4.8M proporsional
            bagian_fasilitas = (4_800_000_000 / omzet) * laba
            bagian_non = laba - bagian_fasilitas
            pph = (bagian_fasilitas * 0.11) + (bagian_non * 0.22)
            metode = 'Pasal 31E (fasilitas 50% tarif)'
        else:
            pph = laba * 0.22
            metode = 'Pasal 17 (22%)'

        tarif_efektif = pph / laba if laba > 0 else 0
        return {
            'pph': round(pph, 2),
            'metode': metode,
            'tarif_efektif': f'{tarif_efektif*100:.1f}%',
            'dpp_laba': round(laba, 2),
            'dpp_omzet': round(omzet, 2),
            'jenis': 'Normal',
        }

    # ─── PPh Final (Pasal 4 Ayat 2) ───
    def pph_final_sewa_tanah(self, gross_rent: float) -> Dict:
        """PPh Final atas sewa tanah/bangunan: 10%."""
        sewa = _validate_positive(gross_rent, 'Sewa')
        pph = sewa * 0.10
        return {
            'pph': round(pph, 2),
            'diterima': round(sewa - pph, 2),
            'tarif': '10%',
            'jenis': 'Sewa Tanah/Bangunan',
            'dasar_pengenaan': round(sewa, 2),
            'dasar_hukum': 'PP 34/2017',
        }

    def pph_final_penjualan_tanah(self, sale_price: float) -> Dict:
        """PPh Final atas pengalihan hak tanah/bangunan: 2.5%."""
        harga = _validate_positive(sale_price, 'Harga jual')
        pph = harga * 0.025
        ppn_jual = self.ppn(harga, 11)
        return {
            'pph': round(pph, 2),
            'ppn': ppn_jual['ppn'],
            'tarif': '2.5%',
            'jenis': 'Pengalihan Tanah/Bangunan',
            'dasar_pengenaan': round(harga, 2),
            'dasar_hukum': 'PP 34/2016',
        }

    def pph_final_bunga_deposito(self, interest: float) -> Dict:
        """PPh Final atas bunga deposito/tabungan: 20%."""
        bunga = _validate_positive(interest, 'Bunga')
        pph = bunga * 0.20
        return {
            'pph': round(pph, 2),
            'diterima': round(bunga - pph, 2),
            'tarif': '20%',
            'jenis': 'Bunga Deposito/Tabungan',
            'dasar_pengenaan': round(bunga, 2),
            'dasar_hukum': 'PP 131/2000',
        }

    def pph_final_konstruksi(self, value: float, license_rank: str = 'lainnya') -> Dict:
        """
        PPh Final atas jasa konstruksi.
        license_rank: 'kecil', 'menengah', 'lainnya'
        Tarif:
          - Kecil: 2%
          - Menengah: 3%
          - Lainnya (besar/perorangan): 4%
        """
        nilai = _validate_positive(value, 'Nilai kontrak')
        tarif_map = {'kecil': 0.02, 'menengah': 0.03, 'lainnya': 0.04}
        tariff = tarif_map.get(license_rank.lower(), 0.04)
        pph = nilai * tariff
        return {
            'pph': round(pph, 2),
            'diterima': round(nilai - pph, 2),
            'tarif': f'{tariff*100:.0f}%',
            'jenis': f'Jasa Konstruksi ({license_rank})',
            'dasar_pengenaan': round(nilai, 2),
            'dasar_hukum': 'PP 9/2022',
        }

    def pph_final_pesangon(self, amount: float) -> Dict:
        """
        PPh Final atas pesangon (PP 68/2009).
        0-50jt: 0%, 50-100jt: 5%, 100-500jt: 15%, >500jt: 25%
        """
        nilai = _validate_positive(amount, 'Pesangon')
        lapisan = [(0, 50_000_000, 0.0), (50_000_000, 100_000_000, 0.05),
                   (100_000_000, 500_000_000, 0.15), (500_000_000, float('inf'), 0.25)]
        pph = 0.0
        remaining = nilai
        for lower, upper, rate in lapisan:
            if remaining <= 0:
                break
            bracket = min(remaining, upper - lower)
            pph += bracket * rate
            remaining -= bracket
        return {
            'pph': round(pph, 2),
            'diterima': round(nilai - pph, 2),
            'nilai': round(nilai, 2),
            'jenis': 'Pesangon',
        }

    # ─── PPh 22 ───
    def pph22_impor(self, nilai_impor: float, have_api: bool = True) -> Dict:
        """PPh 22 atas impor.
        - Dengan API: 2.5% dari nilai impor
        - Tanpa API: 7.5% dari nilai impor
        """
        nilai = _validate_positive(nilai_impor, 'Nilai impor')
        tariff = 0.025 if have_api else 0.075
        pph = nilai * tariff
        return {
            'pph': round(pph, 2),
            'dasar_pengenaan': round(nilai, 2),
            'tarif': f'{tariff*100:.1f}%',
            'api': have_api,
            'jenis': 'PPh 22 Impor',
        }

    # ─── Ringkasan Pajak ───
    def summary(self, results: Dict) -> str:
        """Buat ringkasan text dari hasil perhitungan."""
        parts = []
        for key, val in results.items():
            key_label = key.replace('_', ' ').title()
            if isinstance(val, float):
                parts.append(f'{key_label}: Rp {val:,.0f}')
            elif isinstance(val, str):
                parts.append(f'{key_label}: {val}')
            elif isinstance(val, bool):
                parts.append(f'{key_label}: {"Ya" if val else "Tidak"}')
            else:
                parts.append(f'{key_label}: {val}')
        return '\n'.join(parts)
