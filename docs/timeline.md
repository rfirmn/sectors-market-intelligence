# TIMELINE PENGEMBANGAN MVP
## Market Intelligence Agent — Sectors Hackathon 2026
**Dokumen Pendamping Teknis untuk `project.md`**

---

## 1. Ringkasan Eksekutif & Prinsip Eksekusi

Dokumen ini memetakan seluruh kebutuhan yang tertuang dalam [project.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/project.md) ke dalam jadwal kerja terstruktur, berurutan, dan terukur. Target utama adalah menghasilkan produk MVP yang solid, berfungsi penuh dengan data live Sectors, terverifikasi keandalannya, dan siap dipresentasikan dalam video demo serta repository publik.

### Tiga Aturan Pengendali Timeline (Berdasarkan §0 & §11 `project.md`):
1. **Loop Integrity First**: Setiap fase harus memperkuat loop `DISCOVER → RESEARCH → CHALLENGE` (atau siklus teknis `NUMERICAL → LINGUISTIC → NUMERICAL`).
2. **Fixed Thresholds Prior to Demo Calibration**: Parameter matematika (winsorizing 1%/99%, threshold discrepancy `1.0` dan `1.5`) dikunci di README pada fase awal sebelum memilih kandidat demo, guna mencegah *data-snooping*.
3. **Demo Reliability without Faking**: Komputasi numerik wajib berjalan asli dari live Sectors API, dengan layer *state snapshot caching* transparan sebagai penyelamat jika terjadi gangguan koneksi/rate limit saat recording.

---

## 2. Pemetaan Kebutuhan Sistem (System Requirements Breakdown)

Berdasarkan analisis menyeluruh terhadap [project.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/project.md), berikut adalah 10 modul esensial yang wajib dibangun beserta dependensinya:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE DEPENDENCY FLOW                        │
└────────────────────────────────────────────────────────────────────────┘

 [MODUL 1: Sectors API / MCP Integration & Ingestion]
       │
       ▼
 [MODUL 2: Market State Engine] ─── (Eksklusi Finansial + Winsorized Median/MAD)
       │
       ▼
 [MODUL 3: Opportunity Discovery & Priority Engine] ─── (Discrepancy z-score: 1.0 / 1.5)
       │
       ├────────────────────────────────────────┐
       ▼                                        ▼
 [MODUL 4: Smart Research]             [MODUL 5: Confirmation Layer]
 (Mosaic: Filings → Actions → News)    (Net Foreign Flow Directional Check)
       │                                        │
       └──────────────────┬─────────────────────┘
                          ▼
             [MODUL 6: Thesis Engine] 
             (Bull / Counter / Catalyst / Invalidation)
                          │
                          ▼
             [MODUL 7: Numerical Challenge Engine]
             (Base / Conservative / Stress via z-scores)
                          │
                          ▼
             [MODUL 8: Opportunity Memo Synthesizer]
             (Fixed format + Provenance + Disclaimer)
                          │
                          ▼
             [MODUL 9: Frontend UI — 3 Area View]
             (Scan Overview → Priority Feed → Interactive Memo)
                          │
                          ▼
             [MODUL 10: Demo Reliability & Video Production]
```

### Rincian Spesifikasi per Modul:
* **Modul 1 (Sectors Client & Cache)**: Adapter REST/MCP untuk 5 kategori endpoint (Taxonomy, Financials, Daily Transactions, Filings/Actions/News, Net Foreign Flow).
* **Modul 2 (Market State Engine)**: Filter eksklusi finansial, kalkulasi 8 metrik, normalisasi `peer_z` subsektor via Winsorized Median & MAD.
* **Modul 3 (Discovery & Ranking Engine)**: Perhitungan `fundamental_z`, `price_z`, `discrepancy`, klasifikasi `HIGH` (>1.5) / `MEDIUM` (1.0–1.5).
* **Modul 4 (Smart Research Engine)**: Pipeline mosaic LLM 1-pass (Company Filings -> Corporate Actions -> News -> Fallback Web) menghasilkan bullet FOR/AGAINST bersumber.
* **Modul 5 (Confirmation Layer)**: Pengecekan arah net foreign flow terakhir vs discrepancy (`SUPPORTIVE` vs `MIXED/CONTRARY`).
* **Modul 6 (Thesis Engine)**: Formulasi variant perception statement, counter-thesis, catalyst, falsifiable invalidation.
* **Modul 7 (Numerical Challenge Engine)**: Kalkulasi independen 3 skenario z-score (Base: z terobservasi, Conservative: z - 1, Stress: z = 0) dan penentuan survival status.
* **Modul 8 (Opportunity Memo Synthesizer)**: Formatter terstruktur teks/markdown dengan provenance inline dan mandatory non-advisory disclaimer.
* **Modul 9 (UI 3-Area)**: Market Scan Overview, Opportunity Feed, Interactive Memo Viewer (Investigate → Research → Confirmation → Thesis → Challenge → Memo).
* **Modul 10 (Reliability & Packaging)**: Local snapshot caching, anti-overfitting README documentation, dan rekaman demo video hackathon.

---

## 3. Timeline Pengembangan: Sprint 7 Hari (Hackathon Schedule)

Sprint ini dirancang untuk durasi **7 hari intensif**, dapat disesuaikan kecepatannya tanpa mengubah urutan ketergantungan antar-modul.

```
HARI 1: Fondasi & Integrasi Data Sectors
HARI 2: Market State Engine & Normalisasi Statistik (Median/MAD)
HARI 3: Opportunity Discovery, Ranking & Pengujian Universe
HARI 4: Smart Research (Mosaic LLM) & Confirmation Layer (Foreign Flow)
HARI 5: Thesis Engine, Numerical Challenge & Memo Generator
HARI 6: Frontend UI (Overview, Feed, Interactive Memo View)
HARI 7: End-to-End Stress Test, Demo Caching, README & Video Demo
```

---

### HARI 1: Fondasi, Arsitektur & Integrasi Data Sectors

**Fokus Utama**: Menyiapkan pondasi codebase, struktur project, dan konektivitas tangguh ke Sectors API.

| ID | Task | Output / Deliverable |
|---|---|---|
| **T1.1** | Setup repository, lingkungan pengembangan (Python/Node), package manager, linter, dan config `.env`. | Base repo siap, template konfig & credentials. |
| **T1.2** | Buat adapter Sectors Client (REST API / MCP) dengan retry, rate-limiting handler, dan error logging. | Modul client Sectors yang reusable dan tahan error. |
| **T1.3** | Implementasikan layer caching lokal sederhana (JSON/SQLite snapshot) untuk menyimpan response Sectors. | Cache mechanism untuk mempercepat dev loop dan demo safety. |
| **T1.4** | Buat unit test konektivitas untuk 5 endpoint Sectors: Taxonomy, Financials, Daily Quotes, News/Filings, Foreign Flow. | Test suite data ingestion lulus 100%. |

**Milestone Hari 1**: Data Sectors live dapat di-pull dan di-cache secara deterministik untuk universe non-finansial IDX.

---

### HARI 2: Market State Engine & Normalisasi Statistik

**Fokus Utama**: Implementasi matematis 8 metrik finansial, pemisahan sektor finansial, dan normalisasi `peer_z`.

| ID | Task | Output / Deliverable |
|---|---|---|
| **T2.1** | Implementasi parser taksonomi Sectors & filter eliminasi sektor keuangan (perbankan, asuransi, multifinance). | Universe filter teruji (mengecualikan sektor finansial sesuai §6.1). |
| **T2.2** | Implementasi kalkulator 8 metrik core: Revenue Growth, Earnings Growth, Margin Change, ROE, Relative Valuation (PE/PB), Price Return, Peer-relative Growth, Peer-relative Price. | Perhitungan metrik mentah per emiten non-finansial. |
| **T2.3** | Implementasi fungsi statistik: Winsorizing persentil 1% & 99%, Median subsektor, Median Absolute Deviation (MAD). | Modul statistik robust terhadap outlier small-cap IDX. |
| **T2.4** | Perhitungan formula `peer_z(metric)` per subsektor dan perakitan struktur data `CompanyState`. | Dataset `CompanyState` lengkap dengan provenance inline. |

**Milestone Hari 2**: Universe perusahaan non-finansial berhasil dihitung `CompanyState`-nya dengan skor `peer_z` yang adil lintas satuan.

---

### HARI 3: Opportunity Discovery, Ranking & Pengujian Universe

**Fokus Utama**: Membangun Variant Perception Detector dan mengunci threshold sebelum kalibrasi demo.

| ID | Task | Output / Deliverable |
|---|---|---| 
| **T3.1** | Implementasi perhitungan `fundamental_z` (rata-rata revenue growth, earnings growth, margin change) dan `price_z`. | Engine komputasi discrepancy fundamental vs harga. |
| **T3.2** | Implementasi rule discrepancy: `discrepancy = fundamental_z - price_z`, filter threshold 1.0 (kandidat) dan 1.5 (HIGH priority). | Filter relasional compound aktif dengan klasifikasi label. |
| **T3.3** | Implementasi Priority Score & Ranking Engine untuk memilih 1–3 opportunity teratas. | Modul ranking siap menyajikan list emiten teratas. |
| **T3.4** | **Penguncian Parameter A Priori**: Dokumentasikan nilai threshold (1.0 dan 1.5) di README / doc repo sebelum memilih kandidat. | Komitmen anti-data-snooping tercatat secara transparan. |
| **T3.5** | Scan seluruh universe IDX non-finansial untuk mengidentifikasi 2–3 ticker kandidat demo yang riil dan jelas discrepancy-nya. | List ticker kandidat demo live terverifikasi dengan data nyata. |

**Milestone Hari 3**: Pipeline numerik selesai dari raw data sampai Opportunity Feed kandidat. Parameter resmi terkunci.

---

### HARI 4: Smart Research (Mosaic LLM) & Confirmation Layer

**Fokus Utama**: Integrasi data kualitatif Sectors, fallback web search, dan foreign flow confirmation.

| ID | Task | Output / Deliverable |
|---|---|---|
| **T4.1** | Bangun modul penarik evidence kualitatif Sectors bertingkat: 1) Company Filings (insider trading), 2) Corporate Actions, 3) News Articles. | Data aggregator kualitatif multi-endpoint Sectors. |
| **T4.2** | Integrasikan fallback web search ringan (Google/Tavily/DuckDuckGo) jika data kualitatif Sectors tidak mencukupi 2 bullet. | Fallback query generator yang terarah jika news lokal minim. |
| **T4.3** | Bangun prompt Smart Research 1-pass (dua langkah: gap identifikasi data + penjelasan structural vs temporary) dengan output strictly formatted. | 2–4 evidence bullet terpecah dalam `Evidence FOR` & `Evidence AGAINST` dengan sitasi sumber. |
| **T4.4** | Implementasikan Confirmation Layer: cek arah `net_foreign_flow` periode terakhir vs arah `discrepancy`. | Flag output konfirmasi: `SUPPORTIVE` atau `MIXED / CONTRARY`. |

**Milestone Hari 4**: Loop LINGUISTIC selesai: evidence kualitatif terkumpul dalam format mosaic terstruktur beserta konfirmasi aliran dana asing.

---

### HARI 5: Thesis Engine, Numerical Challenge & Memo Generator

**Fokus Utama**: Penulisan thesis terstruktur, stress testing independen 3 skenario, dan pembentukan memo akhir.

| ID | Task | Estimasi | Output / Deliverable |
|---|---|---|---|
| **T5.1** | Implementasikan Thesis Engine prompt: Bull thesis (variant perception format baku), Counter-thesis (termasuk foreign flow contrary), Catalyst, dan Invalidation. | Komponen narasi falsifiable yang tajam dan non-advisory. |
| **T5.2** | Bangun Numerical Challenge Engine (Hitungan murni independen dari LLM): Skenario Base (`fundamental_z`), Conservative (`fundamental_z - 1`), Stress (`fundamental_z = 0`). | Evaluasi survival status (`Thesis survives` vs `Thesis weakens`) dan konversi balik ke metrik persentase/rasio. |
| **T5.3** | Implementasikan Opportunity Memo Generator (Template fixed Markdown/HTML/JSON sesuai §6.8). | Generator memo komprehensif berisi seluruh blok pipeline. |
| **T5.4** | Validasi Kepatuhan Finansial: Pastikan disclaimer non-advisory terpasang dan kosa kata bebas dari BUY/SELL/HOLD. | Audit kepatuhan §1 & §6.11 lolos 100%. |
| **T5.5** | End-to-End Test Backend Pipeline (CLI Runner): Menjalankan pipeline penuh dari ticker input hingga memo markdown tercetak. | Pipeline CLI berjalan utuh dan konsisten. |

**Milestone Hari 5**: Seluruh backend loop `NUMERICAL → LINGUISTIC → NUMERICAL` berfungsi end-to-end dengan output memo siap saji.

---

### HARI 6: Frontend UI — Tiga Area View

**Fokus Utama**: Membangun tampilan antarmuka modern, interaktif, dan premium yang mencerminkan 3 area wajib.

| ID | Task | Output / Deliverable |
|---|---|---|---|
| **T6.1** | Setup Frontend project & Design System (desain visual modern, tipografi jernih Inter/Outfit, tata letak data-dense finansial). | App layout shell dan komponen dasar (Badge, Card, Metric Table). |
| **T6.2** | **Area 1 — Market Scan Overview**: Visualisasi ringkasan pasar (jumlah emiten discan, universe non-finansial, jumlah opportunity ditemukan, distribusi discrepancy). | Header & dashboard metrics bar yang informatif. |
| **T6.3** | **Area 2 — Opportunity Feed**: List 1–3 opportunity cards dengan badge priority (`HIGH` / `MEDIUM`), skor discrepancy, dan metrik kunci. | Feed interaktif dengan transisi mulus saat card dipilih. |
| **T6.4** | **Area 3 — Interactive Memo View**: Visualisasi bertahap alur investigasi: *Investigate → Research Mosaic → Confirmation → Thesis → Challenge Matrix → Final Memo*. | Stepper/drill-down view yang memperlihatkan reasoning produk ke juri. |
| **T6.5** | Polish UI & Interaksi: Pastikan render data cepat, micro-animations halus, dan disclaimer legal terlihat jelas di footer memo. | UI premium, bersih, tanpa tombol order/trading semu. |

**Milestone Hari 6**: Web application frontend berjalan terhubung ke backend, menyajikan 3 area visual yang memikat dan mudah dipahami juri.

---

### HARI 7: Demo Reliability, Dokumentasi, Video & Submission

**Fokus Utama**: Menjamin keandalan demo saat direkam/dinilai, finalisasi README teknis, dan produksi video presentasi.

| ID | Task | Output / Deliverable |
|---|---|---|---|
| **T7.1** | **Demo Reliability Mechanism**: Simpan cached snapshot dari data emiten demo terpilih untuk antisipasi downtime Sectors/Internet. | Offline/fallback mode aktif tanpa mengubah kode komputasi asli. |
| **T7.2** | **Finalisasi README.md**: Tulis penjelasan Variant Perception, Sectors API usage map (§9), penguncian threshold a priori (§6.2), dan arsitektur loop. | README komprehensif, jujur, dan berbobot akademis/profesional. |
| **T7.3** | Buat naskah video presentasi (3–5 menit) berfokus pada: Problem → The Math (Winsorized z-score) → Live Demo (Discover, Research, Challenge) → Output Memo. | Script presentasi terstruktur dan runut. |
| **T7.4** | Rekaman demo video, screen recording alur UI, voiceover, dan visualisasi arsitektur. | Video presentasi final resolusi tinggi. |
| **T7.5** | Final Review terhadap Definition of Done (§10 `project.md`) dan checklist submission Sectors Hackathon. | Repository publik & video siap di-submit. |

**Milestone Hari 7**: Seluruh deliverable hackathon (kode, README, demo reliability, dan video) selesai dan tervalidasi 100%.

---

## 4. Matriks Beban Kerja & Estimasi Jam (Workload Allocation)

| Komponen / Modul | Persentase | Tingkat Risiko |
|---|---|---|
| **Modul 1: Sectors API & Ingestion** | 14% | Sedang (Rate limit / format response) |
| **Modul 2: Market State & Normalisasi Math** | 15% | Rendah-Sedang (Presisi formula MAD) |
| **Modul 3: Discovery & Priority Engine** | 14% | Rendah (Threshold fixed) |
| **Modul 4 & 5: Smart Research & Confirmation** | 14% | Sedang (Prompting LLM, format JSON) |
| **Modul 6 & 7: Thesis & Numerical Challenge** | 15% | Rendah (Logika deterministik) |
| **Modul 8 & 9: Memo Generator & Frontend UI** | 16% | Rendah-Sedang (Aestetik & integrasi) |
| **Modul 10: Reliability, Docs & Video Demo** | 11 Jam | 12% | Sedang (Kualitas rekaman & kejelasan) |
| **TOTAL** | **75 Jam** | **100%** | **Terkendali (Sprint Hackathon Optimal)** |

*Catatan: Alokasi ~75 jam ini ideal untuk tim 1-2 orang dalam rentang waktu 1 minggu (sekitar 10-11 jam/hari) atau dapat dibagi ke beberapa anggota tim secara paralel.*

---

## 5. Rencana Kontinjensi & Mitigasi Risiko

| Risiko Potensial | Dampak | Strategi Mitigasi Terencana |
|---|---|---|
| **Sectors API lambat / rate-limit saat scan penuh** | High | Terapkan batch fetching dengan delay terukur + simpan hasil scan harian dalam snapshot cache lokal. |
| **Tidak ada kandidat dengan discrepancy > 1.5** | High | Jika universe IDX menghasilkan sebaran lebih sempit, sesuaikan threshold ke 0.8 / 1.2 dan catat alasannya secara transparan di README sebagai temuan empiris. |
| **Data kualitatif Sectors (filings/actions) kosong untuk ticker tertentu** | Medium | Fallback teratur ke endpoint Sectors News; jika masih kosong, fallback 1-pass ke query web search terarah. |
| **Halusinasi LLM pada angka finansial** | Critical | **Hard Rule**: LLM tidak pernah menghitung angka. LLM hanya menerima input JSON angka yang sudah dihitung Python dan bertugas menyusun argumen kualitatif. |
| **Koneksi putus saat rekaman video demo** | High | Mechanism fallback (§6.10): Jika request live gagal, sistem otomatis meload snapshot state cache terakhir tanpa merusak tampilan. |

---

## 6. Definition of Done Checklist (Audit Kesiapan Submit)

Sebelum submit ke panitia Sectors Hackathon 2026, checklist berikut wajib bertanda centang:

- [ ] **Universe Scan**: Berhasil menghitung `CompanyState` untuk universe non-finansial dengan subsector `peer_z` (Winsorized Median & MAD).
- [ ] **Eksklusi Finansial**: Sektor perbankan/asuransi tidak tercampur ke dalam discovery universe.
- [ ] **Threshold Terkunci**: Angka `1.0` dan `1.5` tercantum di README sebelum demo dipilih.
- [ ] **Opportunity Terpilih**: Menemukan minimal 1 emiten nyata dengan discrepancy tinggi yang masuk akal diinvestigasi.
- [ ] **Sectors-Native Evidence**: Smart Research menghasilkan minimal 2 bullet evidence dengan minimal 1 bersumber dari endpoint Sectors (bukan web).
- [ ] **Confirmation Layer**: Menampilkan arah Net Foreign Flow real (`SUPPORTIVE` / `MIXED` / `CONTRARY`).
- [ ] **Falsifiable Thesis**: Bull thesis memiliki format variant perception eksplisit dan invalidation condition jelas.
- [ ] **Calibrated Stress Test**: 3 skenario stress test diturunkan langsung dari `peer_z` (Base, Base - 1, z = 0).
- [ ] **Opportunity Memo Lengkap**: Seluruh elemen memo ter-render termasuk disclaimer non-advisory.
- [ ] **Multi-Endpoint Usage**: Repository membuktikan pemanggilan aktif minimal 4 endpoint Sectors yang berbeda.
- [ ] **UI Clean & Responsive**: 3 area (Overview, Feed, Memo View) berjalan interaktif dan tanpa bug.
- [ ] **Video Walkthrough**: Video 3–5 menit menjelaskan prinsip variant perception dan demo live produk.
