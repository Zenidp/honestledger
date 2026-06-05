# perintah.md — Perintah Sesi Claude Code untuk HonestLedger

Tiga perintah ini dipakai setiap hari selama 7 hari pengerjaan.
Salin dan tempel ke Claude Code sesuai situasi.

---

## 1. MULAI (awal sesi baru / pagi hari)

```
Baca context.md di root project ini secara penuh.
Ini adalah memori project HonestLedger.
Setelah membaca, konfirmasi dengan ringkasan singkat:
nama project, tujuan, stack, dan milestone hari ini berdasarkan progress log.
Lalu tunggu instruksi saya.
```

---

## 2. SIMPAN SESI (sebelum tutup / akhir hari)

```
Update context.md bagian PROGRESS LOG:
tandai milestone yang sudah selesai hari ini sebagai [DONE],
tambahkan catatan singkat apa yang dikerjakan dan keputusan baru apa yang dibuat
ke bagian CATATAN TERBUKA jika ada.
Laporkan apa yang sudah diupdate.
```

---

## 3. PANGGIL SESI TERAKHIR (lanjut kerja setelah jeda)

```
Baca context.md, lihat PROGRESS LOG dan CATATAN TERBUKA.
Ringkas: apa yang sudah selesai, apa yang belum, dan apa yang harus dikerjakan sekarang.
Lalu mulai langsung tanpa tanya macam-macam.
```

---

## Alur harian

```
Buka WSL + VS Code + Claude Code
        ↓
Tempel perintah no.3 (panggil sesi terakhir)
        ↓
Kerja seharian bersama Claude Code...
        ↓
Sebelum tutup: tempel perintah no.2 (simpan sesi)
        ↓
Tutup. Besok ulang dari atas.
```

> Catatan: Perintah no.1 dipakai hanya di hari pertama (Hari 1).
> Mulai Hari 2 dan seterusnya, selalu mulai dengan perintah no.3.
