# MARKET INTELLIGENCE AGENT
## Ground Development Document (Final)
### Sectors Hackathon 2026 — Track: Market Intelligence

Dokumen ini adalah **satu-satunya referensi pengembangan**. Ia menggantikan draf MVP sebelumnya dengan menambahkan landasan teori dan formula matematis yang tadinya masih berupa heuristik verbal. Tidak ada jadwal di dokumen ini — hanya spesifikasi apa yang dibangun dan bagaimana cara kerjanya.

---

## 0. Prinsip yang Mengontrol Setiap Keputusan Scope

> Sebuah komponen masuk MVP **hanya jika** ia memperkuat loop DISCOVER → RESEARCH → CHALLENGE, terlihat/terverifikasi oleh juri dari repo dan video, **dan** formula/threshold di dalamnya ditentukan sebelum melihat hasil — bukan diutak-atik sampai kandidat demo terlihat bagus.

Syarat ketiga ini baru (hasil riset di §2). Ia menutup celah *data-snooping*: ilustrasi klasik dari von Neumann bahwa dengan cukup banyak parameter yang bisa diatur, hampir semua bentuk data bisa "dijelaskan" secara meyakinkan padahal cuma kebetulan — dengan empat parameter kita bisa membentuk gajah, dengan lima ekornya bisa digoyangkan. Solusinya bukan menghindari model, tapi mengunci threshold dan bobot lebih dulu, dan mendesainnya untuk seluruh universe perusahaan, bukan dikalibrasi ke satu ticker favorit.

---

## 1. Definisi Produk

**Tagline**
> Discover what matters. Research why. Challenge whether it survives.

**Problem statement**
> Financial analysts cannot deeply research every company in a large and constantly changing market, so they need a way to discover which situations deserve attention before spending research time.

**Solution statement**
> Market Intelligence Agent scans the market for unusual and meaningful configurations, investigates only the highest-priority opportunities, and challenges the resulting thesis with numerical evidence.

**Persona utama:** Junior Equity Analyst — bisa meneliti satu perusahaan secara dalam, tidak semua perusahaan. Produk berperan sebagai *research allocator*.

**Positioning wajib (syarat kepatuhan hackathon, bukan pilihan gaya):** alat riset dan prioritisasi, bukan penasihat keuangan. Output selalu memakai vocabulary `HIGH-PRIORITY OPPORTUNITY` / `WATCH` / `RESEARCH FURTHER` / `THESIS FRAGILE`, tidak pernah `BUY` / `SELL` / `HOLD`. Disclaimer wajib tampil di tiap memo:
> *"This is a research-prioritization tool, not financial advice. It does not predict returns or guarantee outcomes."*

---

## 2. Landasan Teori (Kenapa Sistem Ini Bekerja, Bukan Cuma Terlihat Bekerja)

Bagian ini mendokumentasikan kerangka yang menjustifikasi tiap komponen numerik dan linguistik di sistem — supaya klaim "kami tidak sekadar pakai LLM" punya dasar yang bisa dijelaskan satu-dua kalimat ke juri.

**Variant Perception / Expectations Investing.** Inti dari opportunity discovery ini bukan konsep baru — ini kerangka yang dipakai investor profesional secara luas. Michael Steinhardt mendefinisikan variant perception sebagai memegang pandangan berdasar yang berbeda secara berarti dari konsensus pasar. Michael Mauboussin membingkainya lebih tajam: kesalahan terbesar dalam investasi adalah gagal membedakan pengetahuan tentang fundamental perusahaan dari ekspektasi yang sudah tersirat di harga pasar. Pendekatan Mauboussin & Rappaport membaca dulu ekspektasi yang tersirat dari harga saat ini, baru membandingkannya dengan pandangan sendiri — inilah metode formal di balik pertanyaan "kenapa market belum repricing."

**Second-Level Thinking (Howard Marks).** Alasan sistem ini punya counter-thesis, bukan cuma thesis: thesis yang baik selalu diuji terhadap apa yang sudah dipercaya konsensus, bukan berdiri sendiri — cara berpikir tingkat pertama berhenti di "perusahaan ini bagus," cara berpikir tingkat dua bertanya apakah pasar sudah tahu itu dan sudah menghargainya secara berlebihan atau belum cukup.

**Mosaic Theory.** Ini yang menjustifikasi bagaimana Smart Research mengumpulkan evidence: analyst profesional membentuk kesimpulan dengan merangkai banyak "tile" kecil dan legal — SEC filings, transkrip earnings call, catatan kaki laporan, data industri — bukan dari satu sumber besar. AI dan machine learning sekarang dipakai justru untuk mempercepat pengumpulan dan peringkasan tile-tile ini, sehingga analyst bisa fokus pada evaluasi, bukan pengumpulan manual. Ini persis peran LLM di sistem: mempercepat sintesis mosaic, bukan menggantikan penilaian.

**Composite scoring sederhana yang terbukti bekerja.** Piotroski F-Score (sembilan tes biner terhadap laporan keuangan, tiap tes lolos dapat satu poin) dan Altman Z-Score (kombinasi linear rasio finansial dengan koefisien tetap yang diestimasi dari data historis) adalah bukti bahwa skor sederhana, tetap, dan bisa dijelaskan sering mengalahkan model yang terlihat canggih — **selama bobotnya ditentukan sekali, bukan diutak-atik**. Detail penting dari Altman: formulanya berbeda untuk tiap tipe perusahaan (manufaktur vs non-manufaktur vs varian emerging market dengan konstanta tambahan). Ini menjadi dasar keputusan di §6.1 bahwa sektor keuangan tidak bisa memakai rule generik yang sama.

**Cross-sectional z-score normalization.** Ini jawaban matematis untuk "bagaimana menggabungkan metrik dengan satuan berbeda secara adil" — growth dalam persen, margin dalam poin persentase, valuasi dalam kelipatan (x). Praktik standar: standardisasi dilakukan di dalam kelompok sebanding (intra-industry/subsektor), bukan lintas seluruh pasar, dan cross-section perlu di-*winsorize* pada persentil ekstrem sebelum distandardisasi supaya satu outlier tidak merusak seluruh ranking. Metrik yang paling tidak terpengaruh nilai ekstrem terbukti menjadi basis ranking yang lebih baik — mendukung penggunaan median/MAD, bukan mean/std mentah, untuk universe IDX yang punya banyak small-cap dengan sebaran ekstrem.

---

## 3. Kesesuaian dengan Kriteria Hackathon

- **Track Market Intelligence**: mensyaratkan derived insight (signal/score, ranking, screener custom logic, comparative analysis, synthesized research) — dipenuhi oleh seluruh pipeline di bawah.
- **Sectors sebagai core dependency**: dipenuhi karena Market State Engine (§6.1) adalah fondasi seluruh pipeline, dan Smart Research (§6.4) memprioritaskan endpoint tekstual Sectors sebelum sumber eksternal.
- **Tidak ada automated trade execution** — tidak pernah ada tombol eksekusi order, bahkan sebagai mock.
- **Tidak boleh memberi nasihat finansial** — dipenuhi lewat vocabulary output dan disclaimer (§1).
- **Technical depth dinilai dari repo**, termasuk apakah "faked for the demo" — dijawab lewat Demo Reliability Mechanism (§6.10): input dikontrol, komputasi tetap asli.

---

## 4. Loop Inti

**Product loop:**
```
DISCOVER → RESEARCH → CHALLENGE
```

**Technical loop:**
```
NUMERICAL → LINGUISTIC → NUMERICAL
```

**Loop dalam istilah variant perception (versi presisi dari technical loop di atas):**
```
Market State (numerik)
      ↓
Implied Expectation vs Actual Fundamental (numerik — di mana gap-nya?)
      ↓
Evidence Gathering (linguistik — mosaic dari sumber Sectors + eksternal)
      ↓
Thesis: kenapa gap ini valid atau tidak (linguistik)
      ↓
Confirmation: apakah broker/foreign flow searah (numerik, ringan)
      ↓
Numerical Challenge: apakah thesis bertahan saat asumsi dilemahkan (numerik)
```

Pembagian kerja yang tidak boleh dilanggar: LLM boleh menyusun pertanyaan, mensintesis evidence, membentuk thesis. LLM tidak boleh menghitung metrik, mengarang angka, atau mengubah formula agar hasil terlihat menarik. Formula = fixed. Parameter = bounded dan ditentukan sebelum lihat hasil. Data = dynamic. Thesis = probabilistic.

---

## 5. Arsitektur MVP

```
SECTORS DATA (REST API / MCP)
        │
        ▼
MARKET STATE ENGINE               (§6.1 — hitung metrik + z-score peer-normalized)
        │
        ▼
OPPORTUNITY DISCOVERY ENGINE      (§6.2 — 1 signal type, threshold fixed a priori)
        │
        ▼
RESEARCH PRIORITY                 (§6.3 — ranking dari z-score yang sama)
        │
        ▼
SMART RESEARCH + LLM              (§6.4 — mosaic: Sectors-native dulu, lalu web)
        │
        ▼
CONFIRMATION LAYER                (§6.5 — broker/foreign flow, satu cek terarah)
        │
        ▼
THESIS ENGINE                     (§6.6 — bull / counter / catalyst / invalidation)
        │
        ▼
NUMERICAL CHALLENGE ENGINE        (§6.7 — 3 skenario, dikalibrasi dari peer distribution)
        │
        ▼
OPPORTUNITY MEMO                  (§6.8 — output akhir)
```

Delapan blok ini adalah keseluruhan sistem. Tidak ada multi-agent swarm atau ML pipeline terpisah. Discovery menyediakan *Research Mandate* terstruktur agar pengguna dapat mengurutkan peluang riset sesuai kriteria yang eksplisit tanpa mengubah ground truth numerik.

---

## 6. Spesifikasi Fitur — CORE (Wajib Dibangun)

### 6.1 Market State Engine

**Fitur yang dihitung — dibatasi 8:**
1. Revenue growth
2. Earnings growth
3. Margin (dan perubahannya)
4. ROE
5. Valuasi relatif (PE atau PB vs median peer)
6. Price return (periode berjalan)
7. Peer-relative growth
8. Peer-relative price performance

**Formula normalisasi (baru — pengganti heuristik verbal):**

```
peer_z(metric) = (company_metric − median(peer_group_metric))
                 / (1.4826 × MAD(peer_group_metric))

peer_group = cohort subsektor dan periode yang sama (termasuk perusahaan yang dinilai)
nilai ekstrem di-winsorize pada persentil 1% / 99% sebelum median & MAD dihitung
```

**Revisi validitas 2026-09-13:** numerator tetap mentah; winsorizing tidak membatasi
skor individual. Growth peer_z hanya memakai YoY. Per keluarga metrik dipilih cohort
periode persis yang paling banyak tersedia, periode terbaru jika jumlah seri.
`n<3`, MAD nol, atau angka tidak valid menghasilkan `None`, bukan nol.
`n=3..7` ditandai `low_sample`. Faktor 1.4826 memberi normal consistency
asimptotik; ia tidak mengalibrasi probabilitas threshold komposit.
Lihat [audit dan simulasi](engine_design_review_and_simulation.md).

Semua metrik dalam discovery dinormalisasi ke skala relatif terhadap peer.
Kesamaan unit skor tidak menjamin kesetaraan informasi atau risiko setiap metrik.

**Pengecualian sektor keuangan (keputusan scope, bukan bug):** perusahaan di sektor perbankan/asuransi/multifinance memakai struktur laporan keuangan berbeda (net interest income, gross loan, total deposit, bukan revenue/margin konvensional). MVP **mengecualikan sektor keuangan dari universe discovery** — bukan memaksakan rule yang sama untuknya. Ini konsisten dengan preseden Altman Z-Score yang memakai formula berbeda per tipe perusahaan.

**Company State — struktur data:**
```
CompanyState
- company_id, company_name, sector, subsector
- revenue_growth, earnings_growth, margin, roe
- valuation_relative, price_return
- peer_relative_growth_z, peer_relative_price_z
- timestamp
```

**Provenance:** setiap angka di memo akhir menyertakan periode, formula, sumber — teks inline, bukan sistem lineage terpisah.

---

### 6.2 Opportunity Discovery Engine — Variant Perception Detector

**Signal dasar:** Fundamental–Price Dislocation. Discovery juga dapat menyajikan lensa growth, profitabilitas operasional, dan PB relatif sebagai kriteria ranking yang dipilih pengguna. Keempatnya adalah screen untuk prioritas riset, bukan prediksi return.

**Definisi discrepancy (formula tetap, ditentukan sebelum lihat hasil):**
```
fundamental_z = average( z(revenue_growth), z(earnings_growth), z(margin_change) )
price_z       = z(price_return)

discrepancy   = fundamental_z − price_z

THRESHOLD (fixed, ditulis di README sebelum development jalan):
  discrepancy > 1.0  → opportunity candidate
  discrepancy > 1.5  → HIGH priority
```

**Kontrak untuk implementasi discovery berikutnya:** hitung discrepancy hanya jika
ketiga growth z dan price z tersedia. Jangan mengisi missing dengan nol atau
merata-ratakan hanya komponen yang ada. Tampilkan fundamental_z dan price_z
terpisah; discrepancy positif tidak membuktikan valuasi murah. Gate tambahan
fundamental_z > 0 adalah hipotesis pengembangan yang belum diaktifkan/dibacktest.

**Catatan kejujuran teknis (tidak berubah dari draf sebelumnya, tetap berlaku):** ini secara implementasi adalah compound relational filter, hanya sekarang dengan basis statistik yang jelas (z-score, bukan threshold tebakan). Klaim yang aman untuk video/README: *"a relational, peer-normalized screener grounded in cross-sectional z-scoring — not a single-metric threshold filter."*

**Disiplin anti-overfitting:** threshold `1.0` dan `1.5` adalah aturan triase tetap,
bukan batas signifikansi. Jangan menyesuaikannya untuk menghasilkan kandidat demo.
Perubahan metodologi memerlukan versi baru, alasan tertulis, dan evaluasi pada
periode yang belum digunakan memilih perubahan; mencatat perubahan saja tidak
menghapus selection bias.

---

### 6.3 Research Priority dan Research Mandate

`discrepancy` tetap satu-satunya label HIGH/MEDIUM dengan threshold tetap pada §6.2. Untuk ranking yang dipersonalisasi, pengguna memilih preset atau bobot eksplisit untuk lensa dislocation, growth, profitability, dan value. Mesin menghitung percentile empiris pada cohort subsektor lengkap sebelum filter mandate diterapkan, lalu menghitung `research_fit = 100 × Σ(weight × lens_score)`.

Mandate dapat membatasi universe, metrik raw, market cap, usia data, dan konsentrasi subsektor. Semua filter bersifat transparan; data yang hilang tidak diimputasi dan hasil kosong tidak melonggarkan kriteria. Skor fit bukan probabilitas dan tidak mengganti label discrepancy.

---

### 6.4 Smart Research — Mosaic Evidence Gathering (LLM, Satu Pass)

**Pertanyaan riset (format dua langkah, expectations-investing):**

```
Langkah 1 (dijawab dari data, bukan LLM):
  Apa arah pergerakan fundamental (z-score) dibanding
  arah pergerakan harga (z-score) dalam periode yang sama?
  → ini yang mendefinisikan "gap" yang perlu dijelaskan.

Langkah 2 (dijawab LLM + evidence):
  Apakah gap ini terjadi karena market belum menyadari
  perubahan fundamental (mispricing sementara), atau karena
  market punya alasan sah untuk skeptis (perbaikan tidak
  struktural)?
```

**Urutan sumber evidence (prinsip mosaic — sumber terstruktur dulu, baru pencarian umum):**
1. Sectors — Company Filings (insider trading / transaksi pemegang saham mayoritas)
2. Sectors — Corporate Actions
3. Sectors — News Articles
4. Baru jika ketiganya tidak cukup: web search umum

**Output:** 2–4 evidence bullet, dipisah FOR / AGAINST, masing-masing dengan sumber tercantum:
```
Evidence FOR
✓ ...
✓ ...

Evidence AGAINST
⚠ ...
⚠ ...
```

Tidak ada loop iteratif, tidak ada stopping-condition logic terpisah — satu pass, hard stop.

---

### 6.5 Confirmation Layer — Broker & Foreign Flow (Baru, Ringan, Sectors-Distinctive)

**Tujuan:** satu cek arah tambahan yang murah dibangun tapi sulit ditiru pakai API finansial generik manapun, karena data broker-level dan foreign-flow historis semacam ini bukan hal umum di luar Sectors untuk pasar IDX.

```
IF net_foreign_flow (simbol, periode terakhir) searah dengan discrepancy
   → confirmation: SUPPORTIVE
ELSE
   → confirmation: MIXED / CONTRARY (masuk sebagai bagian counter-thesis)
```

Ini bukan model prediktif, hanya satu angka arah yang ditampilkan sebagai satu baris tambahan di memo. Tidak perlu regresi, tidak perlu scoring gabungan — cukup arah net flow dibandingkan arah discrepancy.

---

### 6.6 Thesis Engine

Empat komponen tetap:

- **Bull thesis (variant perception statement)** — diformat eksplisit sebagai: *"Pandangan kami tentang [metrik] berbeda dari yang tersirat di harga karena [alasan], dan perbedaan ini [terjustifikasi/belum terjustifikasi] oleh evidence."*
- **Counter-thesis** — alasan utama thesis bisa salah (termasuk kalau confirmation layer MIXED/CONTRARY).
- **Catalyst** — apa yang bisa mengubah ekspektasi pasar.
- **Invalidation** — kondisi yang membatalkan thesis.

Thesis harus falsifiable:
```
SALAH: "Company A is fundamentally strong."
BENAR: "Recent margin expansion may be sustainable because pricing
        power appears sufficient to offset higher input costs."
```

---

### 6.7 Numerical Challenge Engine — 3 Skenario, Dikalibrasi dari Peer Distribution

**Perubahan dari draf sebelumnya:** skenario tidak lagi berupa angka yang "kelihatan masuk akal" tapi ditebak. Sekarang diturunkan langsung dari z-score yang sudah dihitung di §6.1:

```
BASE            fundamental_z saat ini (kondisi terobservasi)
CONSERVATIVE    fundamental_z − 1  (mundur satu deviasi peer)
STRESS          fundamental_z = 0  (reversion penuh ke median peer)
```

Nilai z ini diterjemahkan kembali ke angka growth/margin/valuasi untuk keperluan narasi di memo (format tabel seperti sebelumnya), tapi basis perhitungannya sekarang bisa dijelaskan satu kalimat: *"Conservative dan Stress adalah seberapa jauh perusahaan harus mundur menuju rata-rata sektornya, bukan angka yang ditebak."*

**Output — tiga status, bukan confidence numerik:**
```
BASE            Thesis survives
CONSERVATIVE    Thesis survives
STRESS          Thesis weakens
```

**Arsitektur wajib (tidak berubah):** LLM mengusulkan hipotesis, engine numerik menghitung hasil skenario secara independen, LLM menerima hasil dan memperbarui thesis. LLM tidak pernah menghitung angka sendiri.

---

### 6.8 Opportunity Memo — Output Akhir

```
━━━━━━━━━━━━━━━━━━━━━━
OPPORTUNITY

COMPANY A
Signal: Fundamental–Price Dislocation
Discrepancy z-score: 1.8 (HIGH)

WHY IT WAS DISCOVERED
Revenue growth          +18%
EPS growth              +23%
Margin                  +4.2pp
Price performance        +2%
vs sector (peer-normalized z): fundamental +1.8, price −0.4

WHAT WE INVESTIGATED
Is the fundamental improvement structural, or has the market
correctly priced in reasons to stay skeptical?

FLOW CONFIRMATION
Net foreign flow: SUPPORTIVE (net buy, last period)

THESIS
[bull thesis — variant perception statement]

COUNTER-THESIS
[counter thesis]

STRESS TEST
Base            Thesis survives
Conservative    Thesis survives
Stress          Thesis weakens

KEY INVALIDATION
[invalidation condition]

NEXT CATALYST
[catalyst]

RESEARCH STATUS
HIGH PRIORITY — RESEARCH FURTHER
THESIS: MODERATELY ROBUST

Disclaimer: This is a research-prioritization tool, not
financial advice. It does not predict returns or guarantee
outcomes.
━━━━━━━━━━━━━━━━━━━━━━
```

---

### 6.9 UI — Tiga Area

1. **Market Scan Overview** — jumlah perusahaan discan, jumlah opportunity ditemukan.
2. **Opportunity Feed** — 1–3 opportunity, diurutkan dari priority_score.
3. **Memo View** — alur klik: *Investigate → Research → Confirmation → Thesis → Challenge → Final Memo*.

Tidak ada filter kompleks, tidak ada halaman setting, tidak ada akun/login.

---

### 6.10 Demo Reliability Mechanism

- Kandidat demo dipilih dari hasil discovery yang sudah pasti menghasilkan discrepancy jelas — **input dikontrol, komputasi tetap real dari data live, bukan output di-hardcode.**
- Fallback ke state yang berhasil diambil sebelumnya jika API/pencarian gagal saat rekaman, bukan diam/error.

---

### 6.11 Elemen Kepatuhan

- Disclaimer "not financial advice" tampil di setiap memo.
- Tidak ada elemen UI yang menyerupai eksekusi order.
- Vocabulary output selalu non-advisory (§1).

---

## 7. Dihapus dari Scope

| Komponen yang dihapus | Alasan |
|---|---|
| Signal tambahan (Peer Divergence, Financial State Change) | Satu signal yang dijelaskan mendalam > tiga signal dangkal. |
| Loop riset iteratif + stopping-condition logic | Satu pass yang solid lebih andal untuk demo. |
| Model prediktif penuh dari broker/foreign flow (GNN, dsb.) | Confirmation layer di §6.5 sudah menangkap nilai intinya dengan satu cek arah; model penuh menambah risiko tanpa menambah bobot penilaian yang sepadan. |
| ML anomaly ranking / clustering / regime detection | Track menyatakan ML opsional; risiko lebih besar dari manfaatnya. |
| Arsitektur multi-agent / branding "N-agent system" | Loop yang jelas lebih meyakinkan daripada jumlah agent. |
| DCF / WACC / financial modeling penuh | Discovery yang menyebabkan DCF dijalankan lebih menarik daripada DCF itu sendiri. |
| Sistem data-lineage/provenance terpisah | Provenance cukup sebagai teks inline di memo. |
| Breakdown visual skor berbobot | priority_score tunggal + label HIGH/MEDIUM sudah cukup. |
| Akun pengguna, autentikasi, multi-user | Tidak relevan untuk produk yang dinilai lewat video dan repo. |
| Skor confidence numerik di mana pun | Robustness label (Survives/Weakens) lebih jujur. |
| Sektor keuangan dalam universe discovery v1 | Struktur laporan keuangannya berbeda; dikecualikan secara eksplisit, bukan dipaksakan (§6.1). |

---

## 8. Batas Kedalaman Teknis untuk Fitur yang Tetap Masuk Scope

- **Peer normalization**: cukup median + MAD per subsektor dengan winsorizing 1%/99%. Jangan bangun model distribusi yang lebih canggih (kernel density, dsb.).
- **Discovery rule**: threshold z-score tetap dua angka (1.0 / 1.5), dikunci di README sebelum tuning kandidat demo.
- **Smart Research**: 1 pertanyaan riset dua-langkah, 1 pass, maksimal 4 sumber terurut (3 Sectors-native + 1 fallback web), 2–4 evidence bullet.
- **Confirmation layer**: satu perbandingan arah, bukan model. Jangan tergoda menambah bobot/weighting ke confirmation.
- **Numerical challenge**: 3 skenario, diturunkan dari z-score yang sudah ada — jangan bangun tabel asumsi terpisah per perusahaan.
- **Memo**: satu template tetap.
- **UI**: tidak ada dark/light toggle, tidak ada halaman pengaturan.

---

## 9. Peta Prioritas Data Sectors per Tahap Pipeline

| Tahap | Endpoint Sectors yang dipakai |
|---|---|
| Market State Engine | Company quarterly financials, daily transaction data, subsector/industry taxonomy, free float |
| Opportunity Discovery | (turunan dari Market State, tidak ada endpoint baru) |
| Smart Research | Company Filings (insider trading), Corporate Actions, News Articles |
| Confirmation Layer | Daily net foreign inflow per symbol |
| Sector exclusion check | Daftar industri/subindustri (untuk mengidentifikasi & mengecualikan sektor keuangan) |

Peta ini penting untuk video/README: menunjukkan bahwa hampir semua tahap pipeline memakai endpoint Sectors yang berbeda dan saling melengkapi — bukan cuma satu endpoint fundamental yang dipanggil berkali-kali.

---

## 10. Definition of Done (Fungsional)

- Market state dihitung untuk seluruh universe non-finansial yang tersedia dari Sectors, dengan peer_z terhitung benar per subsektor.
- Threshold discovery (1.0 / 1.5) tercatat di README sebagai angka yang dikunci sebelum kandidat demo dipilih.
- Minimal satu opportunity valid ditemukan dari data real dan bisa dijelaskan end-to-end.
- Smart Research menghasilkan minimal dua evidence bullet dengan sumber tercantum, dengan minimal satu di antaranya berasal dari endpoint Sectors-native (bukan web search).
- Confirmation layer menampilkan status SUPPORTIVE/MIXED/CONTRARY berdasarkan data foreign flow real.
- Thesis, counter-thesis, catalyst, invalidation semua terisi dengan klaim falsifiable.
- Tiga skenario numerical challenge dihitung dari z-score yang sama dengan discovery, bukan angka independen.
- Memo akhir merender lengkap termasuk disclaimer.
- Kode di repository menunjukkan pemanggilan Sectors API/MCP yang nyata di lebih dari satu endpoint, bukan data mock statis.
- Seluruh alur bisa direkam dalam satu take tanpa berpura-pura di bagian mana pun.

---

## 11. Prinsip yang Menjaga Dokumen Ini Tetap Berlaku

Uji tiga pertanyaan sebelum menambah apa pun di luar dokumen ini:

1. Apakah ini memperkuat loop DISCOVER → RESEARCH → CHALLENGE?
2. Apakah ini akan terlihat dan bisa diverifikasi juri dari repo dan video?
3. Apakah formula/threshold di dalamnya ditentukan sebelum melihat hasil, bukan sesudah?

Jika jawabannya tidak untuk salah satu, itu bukan MVP — walau secara konsep menarik.
