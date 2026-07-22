# Changelog

Semua perubahan penting proyek ini dicatat di sini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.0.0/),
dan proyek memakai [Semantic Versioning](https://semver.org/lang/id/).

## [1.1.0] — 2026-07-22

### Added
- Log **PPh 21** (web + Android) dengan auto-calc dari `TaxCalculator.pph21`
- **Laporan periode** (`/reports/period`) berbasis `get_summary_by_period`
- Print preview PDF-like: PPh potongan, laporan periode, log PPh 21
- Export CSV: PPh potongan (filter-aware), PPh 21, laporan periode
- Kalender **bisa disesuaikan user**: deadline berulang (hari 1–31) dan sekali (YYYY-MM-DD)
- CRUD deadline di web + Android
- Edit dokumen penuh (judul/kategori/status/periode/notes) + search
- Dashboard period selector + perbandingan vs bulan sebelumnya
- Android `ReportScreen` (ringkasan periode) + shortcut dari Beranda
- Workflow **Release on tag** (`.github/workflows/release-apk.yml`) → build APK + GitHub Release
- Kalkulator final: pengalihan tanah/bangunan 2,5% dan bunga deposito 20%

### Changed
- Palet UI netral eye-friendly (web + Android)
- Dashboard total bulan/tahun menggabungkan withholding + PPh 21
- Quick actions dashboard mencakup PPh 21, Laporan, Kalender
- `buildozer.spec` version → `1.1.0`
- Bottom nav Android: Beranda · Hitung · Log · PPh21 · Dokumen · Kalender

### Fixed
- Validasi PTKP invalid (raise `ValueError`, bukan silent fallback)
- PPh 21 non-pegawai double-cut
- Delete destructive routes POST-only
- Checkbox `is_recurring` tidak default-on saat unchecked
- Case-insensitive object type matching PPh 23/26
- Amount negatif ditolak di `add_withholding`

### Security
- `SECRET_KEY` dari environment / random fallback (bukan hardcode)

## [1.0.1] — sebelumnya

- Baseline dual-surface Flask + Kivy
- Kalkulator inti, log withholding, dokumen, kalender hardcode
- CI build APK on push to `main`
