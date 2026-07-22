"""
Tax Calculator — Corporate Tax Manager
Perhitungan PPh 21, PPh 23/26, PPN, PPh Badan (Indonesia)
"""

class TaxCalculator:
    """Functions for Indonesian corporate tax calculations."""

    # PTKP status (Kawin/tanggungan)
    PTKP_LAJANG = 54_000_000       # TK/0
    PTKP_KAWIN = 4_500_000         # Tambahan jika kawin
    PTKP_TANGGUNGAN = 4_500_000    # Per tanggungan (max 3)
    PTKP_KHUSUS = 54_000_000       # Pekerjaan khusus (tambahan)

    # Tarif PPh 21 Pasal 17 (lapisan)
    LAPISAN = [
        (0, 60_000_000, 0.05),
        (60_000_000, 250_000_000, 0.15),
        (250_000_000, 500_000_000, 0.25),
        (500_000_000, 5_000_000_000, 0.30),
        (5_000_000_000, float('inf'), 0.35),
    ]

    # Tarif PPh 23
    TARIF_PPH23 = {
        'Dividen': 0.15,
        'Bunga': 0.15,
        'Royalti': 0.15,
        'Jasa': 0.02,
        'Sewa': 0.02,
        'Hadiah': 0.15,
    }

    def pph21_monthly(self, gross_salary: float, dependents: int = 0) -> tuple:
        """
        Hitung PPh 21 masa (monthly) untuk pegawai tetap.
        Returns (pph21_monthly, net_salary, ptkp_description)
        """
        dependents = min(dependents, 3)  # Max 3 tanggungan

        # Biaya jabatan: 5% dari gross, max 500rb/bulan = 6jt/tahun
        biaya_jabatan = min(gross_salary * 0.05 * 12, 6_000_000)

        # Iuran pensiun (asumsi 1% dari gaji, max 200rb/bulan)
        iuran_pensiun = min(gross_salary * 0.01 * 12, 2_400_000)

        # Penghasilan neto setahun
        net_year = (gross_salary * 12) - biaya_jabatan - iuran_pensiun

        # PTKP
        ptkp = self.PTKP_LAJANG + (self.PTKP_KAWIN if dependents >= 0 else 0) + (dependents * self.PTKP_TANGGUNGAN)
        ptkp_desc = f'Rp {ptkp:,.0f} (TK/{dependents})'

        # PKP
        pkp = max(0, net_year - ptkp)

        # PPh 21 setahun (tarif progresif)
        pph_year = 0
        remaining = pkp
        for lower, upper, rate in self.LAPISAN:
            if remaining <= 0:
                break
            bracket = min(remaining, upper - lower)
            pph_year += bracket * rate
            remaining -= bracket

        # PPh 21 sebulan
        pph_monthly = pph_year / 12

        return pph_monthly, gross_salary, ptkp_desc

    def pph23(self, amount: float, obj_type: str = 'Jasa') -> float:
        """
        Hitung PPh 23/26 (withholding tax).
        Returns PPh 23 amount.
        """
        # Default tariff based on object type
        tariff = self.TARIF_PPH23.get(obj_type.title(), 0.02)
        return amount * tariff

    def ppn(self, price: float, tariff_percent: float = 11) -> tuple:
        """
        Hitung PPN (Pajak Pertambahan Nilai).
        Returns (ppn_amount, total_with_ppn)
        """
        ppn = price * (tariff_percent / 100)
        return ppn

    def pph_badan(self, taxable_profit: float, gross_revenue: float) -> float:
        """
        Hitung PPh Badan (Pasal 17 / PP 23 / Pasal 31E).
        Returns PPh Badan amount.
        """
        # Cek apakah memenuhi syarat PP 23 (UMKM dengan omzet < 4.8M)
        # PP 23: 0.5% dari omzet (final) — untuk wajib pajak tertentu
        if gross_revenue <= 4_800_000_000:
            # PP 23: 0.5% dari omzet
            return gross_revenue * 0.005

        # PPh Badan normal: 22% (Pasal 17)
        # Pasal 31E: mendapat fasilitas 50% dari tarif normal untuk PKP
        # sampai dengan 4.8M dari peredaran bruto
        if gross_revenue <= 50_000_000_000:
            # Fasilitas Pasal 31E
            fasilitas_pkp = (4_800_000_000 / gross_revenue) * taxable_profit
            non_fasilitas_pkp = taxable_profit - fasilitas_pkp

            pph = (fasilitas_pkp * 0.11) + (non_fasilitas_pkp * 0.22)
            return pph
        else:
            return taxable_profit * 0.22

    def pph_final_sewa(self, gross_rent: float) -> float:
        """PPh Final atas sewa tanah/bangunan: 10% dari bruto."""
        return gross_rent * 0.10

    def pph_final_penjualan(self, sale_price: float) -> float:
        """PPh Final atas penjualan tanah/bangunan: 2.5% dari bruto."""
        return sale_price * 0.025

    def pph_final_bunga_deposito(self, interest: float) -> float:
        """PPh Final atas bunga deposito: 20% dari bruto."""
        return interest * 0.20
