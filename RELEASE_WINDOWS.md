# Release Windows

Repository ini sudah memakai GitHub Actions untuk membuat installer Windows satu-klik.

## Target output

`AIClipperStudio_Setup_<versi>.exe`

Pengguna akhir cukup:

1. Download installer
2. Double click
3. Next
4. Install
5. Finish

Tidak perlu Python, CMD, Laragon, atau instal FFmpeg manual.

## Build otomatis

Workflow:
`.github/workflows/build-windows.yml`

Workflow berjalan pada:
- push source ke `main`
- manual melalui tab Actions
- tag versi seperti `v0.2.0`

## Catatan Smart App Control / SmartScreen

Installer unsigned tetap dapat menghasilkan file EXE, tetapi Windows dapat memberi peringatan atau memblokirnya.

Untuk release production yang dipercaya Windows, tambahkan sertifikat Code Signing tepercaya dan aktifkan signing pada workflow. Jangan menyimpan password atau file PFX langsung di repository; gunakan GitHub Actions Secrets.
