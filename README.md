# Corporate Tax Manager

**Aplikasi Bantu Bagian Pajak Perusahaan** — Hitung PPh 21, 23, 26, PPN, PPh Badan, PPh Final, catat transaksi potongan, kelola dokumen perpajakan, dan pantau deadline pajak.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.0%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Fitur Lengkap

| Fitur | Deskripsi |
|---|---|
| **Dashboard** | Ringkasan PPh bulan/tahun, statistik, deadline mendatang, akses cepat |
| **Kalkulator PPh 21** | Pegawai tetap + bukan pegawai, PTKP lengkap (TK0–K3), tarif progresif Pasal 17 |
| **Kalkulator PPh 23** | Potongan 2% (Jasa/Sewa) / 15% (Dividen/Bunga/Royalti/Hadiah) |
| **Kalkulator PPh 26** | WPLN (20%), opsi NPWP (beralih ke tarif PPh 23) |
| **Kalkulator PPN** | PPN Dalam Negeri (DPP / sudah termasuk), PPN Impor |
| **Kalkulator PPh Badan** | PP 23 (UMKM 0,5%), Pasal 31E (fasilitas 50%), Pasal 17 (22%) |
| **Kalkulator PPh Final** | Sewa tanah (10%), Konstruksi (2%/3%/4%), Pesangon, PPh 22 Impor |
| **Log PPh 23/26** | CRUD transaksi potongan, filter per tahun/bulan/jenis, export CSV |
| **Manajemen Dokumen** | Catat SPT, Faktur Pajak, Bukti Potong — filter kategori & status |
| **Kalender Pajak** | Visual deadline bulanan (PPN tgl 10, PPh Final tgl 15, PPh 21/23 tgl 20) |
| **Export CSV** | Download data transaksi untuk rekonsiliasi |
| **JSON API** | Endpoint `/api/calculate` dan `/api/dashboard` untuk integrasi |

---

## Cara Menjalankan

### 1. Web App (via Flask — langsung di browser)

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan
python3 web_app.py

# Buka http://localhost:5000
```

### 2. Android APK (via GitHub Actions)

1. Push ke GitHub Anda sendiri
2. Buka **Actions** → **Build Corporate Tax Manager APK** → **Run workflow**
3. Download APK dari **Artifacts**

Atau build via buildozer di Linux desktop:

```bash
cd corporate-tax-manager
buildozer android debug
```

---

## Struktur Proyek

```
corporate-tax-manager/
├── web_app.py              # Flask app (blueprint architecture)
├── main.py                 # Kivy Android app
├── buildozer.spec          # Konfigurasi build APK
├── requirements.txt
├── .env.example
├── data/
│   ├── tax_calculator.py   # Semua kalkulasi pajak
│   └── tax_db.py           # Database layer (SQLite)
├── templates/
│   ├── base.html           # Layout utama (Bootstrap 5, responsive)
│   ├── index.html          # Dashboard
│   ├── calculator.html     # Kalkulator (tab-based, 6 jenis)
│   ├── withholding.html    # Log PPh 23/26 (CRUD + filter + export)
│   ├── documents.html      # Manajemen dokumen
│   └── calendar.html       # Kalender deadline
├── tests/
│   └── test_all.py         # 48 unit/integration tests
└── .github/workflows/
    └── build-tax-apk.yml   # GitHub Actions build APK
```

---

## Kalkulator Pajak yang Tersedia

| Kalkulator | Method | Edge Cases Tested |
|---|---|---|
| PPh 21 Pegawai Tetap | `pph21()` | Gaji nol, gaji < PTKP, gaji tinggi (tarif progresif maks) |
| PPh 21 Bukan Pegawai | `pph21_non_pegawai()` | 50% norma penghitungan |
| PPh 23 | `pph23()` | Zero amount, large amount, invalid type (default 2%) |
| PPh 26 | `pph26()` | Dengan NPWP (→ PPh 23), tanpa NPWP |
| PPN | `ppn()` | DPP, include PPN, berbagai tarif |
| PPN Impor | `ppn_impor()` | Dengan bea masuk |
| PPh Badan | `pph_badan()` | PP 23, Pasal 31E, Pasal 17 |
| Sewa Tanah | `pph_final_sewa_tanah()` | 10% final |
| Konstruksi | `pph_final_konstruksi()` | Kecil 2%, Menengah 3%, Lainnya 4% |
| Pesangon | `pph_final_pesangon()` | Tarif progresif 0%/5%/15%/25% |
| PPh 22 Impor | `pph22_impor()` | Dengan/tanpa API |

---

## Testing

```bash
# Jalankan semua test (48 tests)
pytest tests/test_all.py -v

# Test coverage
pytest tests/test_all.py --cov=data/ --cov-report=term-missing
```

---

## Teknologi

- **Backend:** Python 3, Flask, SQLite
- **Mobile:** Kivy + Buildozer
- **Frontend:** Bootstrap 5, Bootstrap Icons
- **Testing:** pytest, unittest
- **CI/CD:** GitHub Actions (APK build)

---

## Lisensi

MIT — bebas digunakan dan dikembangkan.
