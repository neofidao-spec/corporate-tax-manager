# Changelog

Semua perubahan penting proyek ini dicatat di sini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.0.0/),
dan proyek memakai [Semantic Versioning](https://semver.org/lang/id/).

## [1.1.3] — 2026-07-22

### Added
- Shared CSV export helpers (`data/export_utils.py`) untuk PPh 21, withholding, laporan periode
- Android **Export CSV** di PPh 21, Log PPh 23/26, dan Laporan Periode
- File export tersimpan di `user_data_dir/exports/` (popup path + total)

### Changed
- Web `/pph21/export`, `/withholding/export`, `/reports/period/export` memakai helper yang sama
- `buildozer.spec` / footer version → `1.1.3`

## [1.1.2] — 2026-07-22

### Added
- Skip-link, landmark `<main>`, `aria-current`, `aria-busy`, flash region `aria-live`
- Token kontras status: `--success-text`, `--warning-text`, `--danger-text`, `--info-text`
- `status-chip` (ok / soon / overdue) untuk deadline dashboard

### Changed
- Badge/alert soft-bg memakai teks lebih gelap + border (baca lebih jelas)
- Alert body text gelap + strip kiri berwarna
- Android status colors diselaraskan ke token lebih gelap
- `prefers-reduced-motion` menonaktifkan animasi skeleton
- `buildozer.spec` / footer version → `1.1.2`

## [1.1.1] — 2026-07-22

### Added
- Density toggle web (**Ringkas / Lega**) + skeleton loading shimmer
- Density compact Android (tombol Beranda) dengan **persist ke `ctm_prefs.json`**
- Empty-state konsisten (judul + penjelasan + CTA) di semua halaman list/report
- Banner **Reminder deadline** (LEWAT/SEGERA) di dashboard web + Android

### Changed
- Decision-first KPI hierarchy (hero metric) di dashboard & laporan
- `buildozer.spec` / footer version → `1.1.1`

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
