# Corporate Tax Manager

**Aplikasi Bantu Bagian Pajak Perusahaan** — Hitung PPh 21, 23, 26, PPN, PPh Badan, PPh Final, catat transaksi potongan, kelola dokumen perpajakan, dan pantau deadline pajak.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.0%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Fitur Lengkap

| Fitur | Deskripsi |
|---|---|
| **Dashboard** | Ringkasan PPh bulan/tahun (withholding + PPh 21), MoM comparison, chart, quick actions |
| **Kalkulator PPh 21** | Pegawai tetap + bukan pegawai, PTKP lengkap (TK0–K3), tarif progresif Pasal 17 |
| **Kalkulator PPh 23** | Potongan 2% (Jasa/Sewa) / 15% (Dividen/Bunga/Royalti/Hadiah) |
| **Kalkulator PPh 26** | WPLN (20%), opsi NPWP (beralih ke tarif PPh 23) |
| **Kalkulator PPN** | PPN Dalam Negeri (DPP / sudah termasuk), PPN Impor |
| **Kalkulator PPh Badan** | PP 23 (UMKM 0,5%), Pasal 31E (fasilitas 50%), Pasal 17 (22%) |
| **Kalkulator PPh Final** | Sewa tanah, Konstruksi, Pesangon, PPh 22 Impor, Pengalihan Tanah 2,5%, Bunga Deposito 20% |
| **Log PPh 23/26** | CRUD transaksi potongan, filter, print preview, export CSV |
| **Log PPh 21** | Payroll log dengan auto-calc, filter, print preview, export CSV |
| **Laporan Periode** | Ringkasan gabungan per bulan/tahun + print + CSV |
| **Manajemen Dokumen** | Search, edit status, edit full, filter kategori/status |
| **Kalender Pajak** | Deadline **user-customizable** (berulang hari 1–31 atau sekali YYYY-MM-DD) |
| **Android (Kivy)** | Paritas fitur: kalkulator, log, PPh 21, dokumen, kalender, laporan periode |
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

**Build artifact (setiap push ke main):**
1. Buka **Actions** → **Build Corporate Tax Manager APK**
2. Download APK dari **Artifacts**

**Release formal (tag):**
```bash
git tag -a v1.1.0 -m "Corporate Tax Manager v1.1.0"
git push origin v1.1.0
```
Workflow **Release Corporate Tax Manager APK** akan:
1. Build APK
2. Membuat GitHub Release
3. Mengunggah file APK ke release

Atau build lokal via buildozer di Linux desktop:

```bash
cd corporate-tax-manager
buildozer android debug
```

---

## Struktur Proyek

```
corporate-tax-manager/
├── web_app.py              # Flask app
├── main.py                 # Kivy Android app
├── buildozer.spec          # Konfigurasi build APK (v1.1.4)
├── CHANGELOG.md
├── requirements.txt
├── .env.example
├── data/
│   ├── tax_calculator.py   # Semua kalkulasi pajak
│   └── tax_db.py           # Database layer (SQLite)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── calculator.html
│   ├── withholding.html
│   ├── pph21.html
│   ├── period_report.html
│   ├── documents.html
│   ├── calendar.html
│   └── print_*.html        # Print-friendly previews
├── tests/
│   └── test_all.py
└── .github/workflows/
    ├── build-tax-apk.yml   # Build APK on push main
    └── release-apk.yml     # Release on tag v*
```

---

## Testing

```bash
# Jalankan semua test
pytest tests/test_all.py -v

# Test coverage
pytest tests/test_all.py --cov=data/ --cov-report=term-missing
```

Saat ini suite mencakup kalkulator, DB, routes web (CRUD, print, export), dan edge cases validasi.

---

## Teknologi

- **Backend:** Python 3, Flask, SQLite
- **Mobile:** Kivy + Buildozer
- **Frontend:** Bootstrap 5, Bootstrap Icons, Inter font, neutral tokens
- **Testing:** pytest, unittest
- **CI/CD:** GitHub Actions (APK build + tag release)

---

## Lisensi

MIT — bebas digunakan dan dikembangkan.
