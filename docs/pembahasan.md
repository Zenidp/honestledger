# Pembahasan Fundamental — HonestLedger

> Dokumen ini adalah ruang brainstorming untuk mempertanyakan dan memperkuat
> fondasi konseptual sistem. Diisi selama sesi diskusi dengan Claude Code.

---

## Sesi 1 — 2026-06-05

### Pertanyaan Kritis #1: Apakah ada kasus AI self-improving di domain rekonsiliasi keuangan?

**Jawaban jujur: Tidak ada yang terdokumentasi.**

Sistem rekonsiliasi yang ada saat ini:

| Sistem | Cara kerja | Self-improving? |
|--------|-----------|-----------------|
| SAP, Oracle, Blackline | Rule-based, manual | ❌ Developer update manual |
| Auditoria, Peakflo | ML matching, retrain periodik | ❌ Manual retraining oleh tim |
| Fraud detection modern | Drift detection → retrain | ⚠️ Semi-otomatis, supervised |

**Implikasi:** HonestLedger bukan menyelesaikan masalah yang sudah ada — melainkan
membangun fondasi untuk masalah yang **pasti datang** seiring industri bergerak ke
otomasi rekonsiliasi berbasis AI.

---

### Pertanyaan Kritis #2: Kenapa program sengaja dibuat salah dulu?

**Masalah dengan demo saat ini:**

Demo memakai v0 yang sengaja di-set sangat ketat (name_similarity=0.95, dll),
kemudian "diperbaiki" oleh sistem sendiri. Ini tidak realistis karena:

> Tidak ada developer yang sengaja membuat programnya salah, lalu dikonfirmasi
> salah oleh programnya sendiri, lalu diperbaiki oleh programnya sendiri.
> Itu buang-buang waktu.

**Yang realistis:** Program bekerja baik pada data lama. Ketika data baru masuk
dengan pola berbeda (akuisisi perusahaan, vendor baru, konvensi penamaan berubah,
struktur fee berubah), program mulai error. Di sinilah self-improvement relevan.

---

### Pertanyaan Kritis #3: Apakah reward hacking terjadi jika AI diprogram dengan benar?

**Jawaban: Ya, karena Hukum Goodhart.**

> *"When a measure becomes a target, it ceases to be a good measure."*
> — Charles Goodhart

Metrik yang dioptimasi (match rate, accuracy terhadap training data) selalu
**proxy yang tidak sempurna** dari tujuan sebenarnya. Agent yang mengoptimasi
proxy bisa menemukan cara memenuhi metrik tanpa memenuhi tujuan sebenarnya.

**Contoh konkret di rekonsiliasi:**
```
Tujuan sebenarnya:  cocokkan payment ke invoice yang BENAR
Metrik yang diukur: match rate (% yang berhasil di-match)

Reward hacking:
  Agent turunkan threshold similarity → lebih banyak "cocok"
  → match rate naik di training data
  → tapi banyak salah di holdout (pola yang tidak pernah dilihat)
```

**Kapan reward hacking terjadi meski "program benar":**
1. **Distribution shift** — data baru punya pola berbeda, agent overfit ke pola baru
2. **Metric imperfection** — train accuracy ≠ real-world accuracy
3. **Shortcut learning** — agent temukan pattern spurious yang tidak generalize

**Kesimpulan:** Reward hacking bukan soal programmer ceroboh — ini sifat fundamental
dari setiap sistem yang mengoptimasi metrik sebagai proxy tujuan.

---

### Arsitektur yang Lebih Masuk Akal (diusulkan pemilik, 2026-06-05)

**Konsep:** Pre-trained multiple versions + Judge sebagai selector

```
Training phase (offline):
  data_historis_diverse → calibrate → v0, v1, v2, v3, v4, ...
  Setiap version dikalibrasi untuk karakteristik data yang berbeda.

Production phase (online):
  data_baru masuk
    → coba v0 (default)
    → jika akurasi rendah:
        Judge: analisis pola error → rekomendasikan v_n yang paling suitable
        Verify: apakah v_n genuine untuk distribusi data ini?
        → Accept: gunakan v_n
        → Reject: coba rekomendasi lain atau flag untuk review manual
```

**Kenapa ini lebih baik:**

1. **Realistis** — mirip cara production ML bekerja (mixture of experts,
   context-dependent model selection)
2. **Jujur** — tidak ada "program sengaja salah"; semua version valid untuk
   konteks datanya masing-masing
3. **Reward hacking masih relevan** — Goodhart's Law tetap berlaku saat selector
   memilih version; holdout test memastikan pilihan generalizes bukan overfits
4. **Defensible ke juri** — tidak bisa dibantah dengan "kenapa sengaja bikin salah?"

**Reward hacking dalam arsitektur baru ini:**

```
Scenario: data_baru dari perusahaan baru (vendor names berbeda)
Judge rekomendasikan: "pakai v3 (name_similarity=0.7) untuk data ini"

Reward hacking check:
  v3 bagus di data_baru (holdout dari distribusi sama)?  → GENUINE
  v3 bagus di data_baru tapi rusak di data_lama?         → REWARD HACKING
    (agent overfits ke distribusi baru, melupakan lama)
```

Holdout set yang mencampur data lama dan baru adalah kuncinya.

---

### Framing yang Lebih Kuat untuk Pitch

**Framing lemah (saat ini):**
> "Kami menunjukkan AI yang sengaja dibuat salah, lalu self-improving,
> dan kami menangkap reward hacking-nya."

**Framing kuat (seharusnya):**
> "Ketika industri rekonsiliasi keuangan bergerak ke AI berbasis self-adaptation
> (dan ini pasti terjadi), sistem perlu mekanisme verifikasi untuk memastikan
> adaptasi rules itu genuine — bukan overfitting ke data terbaru sambil
> melupakan pola lama. HonestLedger membuktikan mekanisme itu bisa dibangun.
> Ini adalah seat belt untuk sistem yang sedang dibangun industri sekarang."

**Fondasi akademik yang mendukung:**
- Goodhart's Law (1975) — optimizing proxy metrics diverges from true objective
- ASG-SI (arxiv 2512.23760) — reward hacking & behavioral drift di self-improvement loop
- EvilGenie (arxiv 2511.21654) — held-out tests + LLM judge untuk deteksi reward hacking
- Lilian Weng (OpenAI, 2024) — "best practice = evaluate against diverse holdout scenarios"

---

### Open Questions untuk Brainstorming Lanjut

1. **Bagaimana membangun holdout set yang representatif** kalau distribusi data
   di masa depan belum diketahui? (Exploratory holdout vs. fixed holdout)

2. **Kapan sebaiknya trigger self-improvement?** Accuracy drop berapa % yang
   signifikan untuk mulai proses judge + verify?

3. **Bagaimana versioning yang tepat?** Apakah versioning linear (v0→v1→v2)
   atau tree-based (v0 → v1a, v1b berdasarkan data cluster)?

4. **Multi-tenant consideration:** Apakah setiap tenant perlu rule version
   yang berbeda? Atau ada "universal best" yang bisa di-share?

5. **Kapan sistem harus fallback ke human?** Jika judge tidak yakin version
   mana yang cocok, dan beberapa propose + verify cycle gagal?
