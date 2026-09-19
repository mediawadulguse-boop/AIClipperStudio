# AI Clipper Local

Project dipivot dari installer Windows menjadi **single-file HTML local** agar pemakaian jauh lebih sederhana.

## Cara pakai

1. Download `AIClipper.html`.
2. Double-click file tersebut.
3. Buka dengan Chrome atau Microsoft Edge terbaru.
4. Pilih video.
5. Klik **Analisis AI**.
6. Pilih kandidat clip.
7. Preview dan export.

Tidak perlu:
- Python
- CMD
- FFmpeg manual
- Laragon
- installer Windows

## Cara kerja

- Video tetap berada di komputer.
- Whisper berjalan langsung di browser melalui Transformers.js.
- Browser mengunduh model AI pada pemakaian pertama lalu menyimpannya di cache.
- Kandidat clip dinilai secara lokal berdasarkan hook, curiosity, conflict, information value, emotion, dan standalone context.
- Export dilakukan melalui kemampuan media browser.

## Catatan

Pemakaian pertama membutuhkan internet untuk mengambil library/model AI. WebGPU di Chrome/Edge direkomendasikan agar analisis lebih cepat.

Versi utama proyek sekarang adalah **HTML Local**, bukan EXE.
