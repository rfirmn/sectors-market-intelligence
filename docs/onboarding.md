# ONBOARDING DEVELOPER & PANDUAN CEPAT PROYEK
## Market Intelligence Agent — Sectors Hackathon 2026

Selamat datang di repositori **Market Intelligence Agent**! Dokumen ini dirancang sebagai panduan orientasi kilat (onboarding) agar pengembang atau anggota tim baru dapat langsung memahami visi produk, batasan cakupan kerja (*scope guardrails*), arsitektur sistem, peta dokumentasi, serta langkah teknis yang harus dieksekusi dari Hari 1 hingga Hari 7.

---

## 1. Visi Produk & Nilai Pembeda (The Elevator Pitch)

### Apa itu Market Intelligence Agent?
Sistem AI berbasis riset kuantitatif dan kualitatif yang mengidentifikasi **discrepancy (anomali/peluang)** antara performa fundamental emiten di Bursa Efek Indonesia (IDX) dengan valuasi pasarnya, memverifikasinya melalui bukti tekstual terkurasi dan data aliran dana bursa (*broker/foreign flow*), serta menghasilkan **Investment Memo interaktif** yang tahan uji numerik.

### Tiga Pilar "Unfair Advantage" Proyek Ini di Hackathon:
1. **Bukan Sekadar Pembungkus LLM (Anti-Hallucination Loop)**:
   LLM tidak dibiarkan menebak angka atau berhalusinasi. Sistem digerakkan oleh siklus ketat:
   $$\text{NUMERICAL (Engine)} \longrightarrow \text{LINGUISTIC (LLM/Research)} \longrightarrow \text{NUMERICAL (Challenge)}$$
2. **Memanfaatkan Kedalaman Data Khas Sectors**:
   Mengombinasikan fundamental kuartalan dengan data mikrostruktur lokal yang langka di API global: **Broker Summary (Bandarmology)**, **Daily Net Foreign Flow**, dan **Keterbukaan Informasi BEI**.
3. **Integritas Metodologi (Anti-Overfitting)**:
   Seluruh parameter matematika (Winsorizing 1%/99%, threshold discrepancy $\ge 1.0$) dikunci sebelum data dianalisis, mencegah kalibrasi buatan demi demo.

---

## 2. Siklus Inti Pipeline (Core Architecture Loop)

Pipeline berjalan dalam 3 fase utama yang saling mengunci:

```mermaid
flowchart LR
    A["1. DISCOVER\n(Market State & Screener)"] -->|"Discrepancy Z >= 1.0"| B["2. RESEARCH\n(Mosaic LLM Evidence)"]
    B -->|"Thesis & Evidence"| C["3. CHALLENGE\n(Confirmation & Numerical Test)"]
    C -->|"Lolos Verifikasi"| D["Interactive Investment Memo"]
    
    style A fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    B fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    C fill:#e8f8f5,stroke:#2e7d32,stroke-width:2px
    D fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
```

1. **DISCOVER (Numerical)**:
   * Menghitung 8 metrik finansial untuk seluruh emiten IDX non-finansial.
   * Melakukan normalisasi statistik per subsektor menggunakan **Median dan MAD (Median Absolute Deviation)** untuk menghasilkan `peer_z`.
   * Menghitung Discrepancy Score: mencari emiten dengan fundamental di atas rata-rata industri namun harganya tertinggal.
2. **RESEARCH (Linguistic)**:
   * Mengumpulkan bukti tekstual menggunakan pendekatan *Mosaic*: memprioritaskan endpoint resmi Sectors (Filings emiten, Aksi Korporasi, Berita Terkurasi) sebelum fallback ke pencarian web.
   * Mensintesis 2–4 poin bukti terverifikasi untuk menjawab akar penyebab anomali.
3. **CHALLENGE (Confirmation & Numerical)**:
   * **Confirmation Layer**: Memeriksa apakah foreign flow atau top broker bursa mendukung (*SUPPORTIVE*) atau berlawanan (*MIXED/CONTRARY*).
   * **Numerical Challenge**: Menguji apakah klaim kualitatif LLM konsisten dengan data keuangan riil sebelum memo diterbitkan.

---

## 3. Batasan Cakupan (Scope Guardrails)

Prinsip utama hackathon: **Kualitas dan keketatan implementasi lebih penting daripada banyaknya fitur yang setengah matang.**

### ✅ IN-SCOPE (Wajib Diselesaikan untuk MVP):
* **Universe**: Seluruh emiten IDX non-keuangan (sektor perbankan, asuransi, multifinance dikecualikan dari engine discovery karena struktur laporan keuangan yang berbeda).
* **Data Ingestion**: Integrasi live ke Sectors API v2 dengan *local snapshot caching* (JSON/SQLite).
* **Market State Engine**: Kalkulasi Winsorizing (1%/99%), Median, MAD, dan Z-Score per subsektor.
* **Smart Research**: Single-pass LLM dengan maksimal 4 sumber terurut (3 Sectors-native + 1 fallback).
* **Confirmation Layer**: Pengecekan arah Foreign Flow & Broker Summary sederhana.
* **Frontend**: Tampilan web minimalis, elegan, dan fungsional (Overview Market, Opportunity Feed, Interactive Memo View).

### ❌ OUT-OF-SCOPE (Dilarang Dikerjakan — Hindari Over-Engineering):
> [!WARNING]
> Jangan membuang waktu untuk fitur-fitur di bawah ini karena sudah secara resmi dipangkas dari scope hackathon:
> * Model prediktif kompleks (GNN, Machine Learning clustering/anomaly ranking).
> * Arsitektur multi-agent swarm yang rumit atau lambat.
> * Fitur live-trading, eksekusi order ke broker, atau auto-rebalancing portofolio.
> * Analisis teknikal charting mendalam (indikator MACD, Fibonacci, Bollinger Band).

---

## 4. Peta Navigasi Dokumentasi (Documentation Sitemap)

Repositori ini telah memiliki dokumentasi teknis yang lengkap dan tersusun rapi:

```
market-intelligence/
└── docs/
    ├── walkthrough.md                  # [CHECKPOINT] Rekam jejak progres pengerjaan & status pengujian live
    ├── project.md                      # [PRD UTAMA] Spesifikasi arsitektur, rumus matematika, dan requirements
    ├── timeline.md                     # [ROADMAP] Jadwal sprint 7 hari & pembagian tugas per modul
    ├── onboarding.md                   # [DOKUMEN INI] Ringkasan kilat untuk orientasi tim & developer
    └── docs_sectors_api/               # [KATALOG API] Dokumentasi lengkap 70 endpoint Sectors API v2
        ├── README.md                   # Index & ringkasan seluruh endpoint
        ├── 00_overview_and_auth.md     # Base URL, API Key, Pagination, Error Codes
        ├── 01_idx_screener_and_taxonomy.md  # Taksonomi subsektor, SQL compound screener, Free Float
        ├── 02_idx_financials_and_reports.md # Laporan keuangan kuartalan, company report, rasio
        ├── 03_idx_transactions_and_rankings.md # OHLCV, market cap harian, indeks, most-traded
        ├── 04_idx_news_filings_and_suspensions.md # Filings BEI, insider trading, berita, suspensi
        ├── 05_idx_brokers_and_foreign_flow.md     # Broker summary, bandarmology, foreign flow
        ├── 06_sgx_singapore_market.md  # Data emiten bursa Singapura (SGX)
        ├── 07_klse_malaysia_market.md  # Data emiten bursa Malaysia (KLSE)
        ├── 08_mining_specialized_data.md # Data komoditas minerba ESDM Indonesia
        └── 09_hackathon_pipeline_mapping.md # Pemetaan langsung endpoint Sectors ke modul kode
```

### Panduan Membuka Dokumen Sesuai Kebutuhan:
* Ingin melihat checkpoint pekerjaan dan rekam jejak pengujian live? Buka [walkthrough.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/walkthrough.md).
* Ingin memahami formula matematika atau aturan bisnis? Buka [project.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/project.md).
* Ingin tahu urutan pengerjaan task harian? Buka [timeline.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/timeline.md).
* Ingin tahu URL, parameter, atau format JSON Sectors? Buka file terkait di [docs_sectors_api/](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/docs_sectors_api).
* Ingin melihat hubungan endpoint Sectors dengan kode yang akan ditulis? Buka [docs_sectors_api/09_hackathon_pipeline_mapping.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/docs_sectors_api/09_hackathon_pipeline_mapping.md).

---

## 5. Ringkasan Eksekusi Sprint 7 Hari

Gunakan pembagian hari dari [timeline.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/timeline.md) sebagai panduan progres harian:

* **Hari 1: Fondasi & Integrasi Data Sectors**
  Setup environment, modul klien HTTP Sectors (retry & rate limit handler), layer caching lokal (`snapshot_cache`), dan unit test konektivitas.
* **Hari 2: Market State Engine & Normalisasi Statistik**
  Filter universe non-finansial, parser data keuangan, Winsorizing 1%/99%, kalkulasi Median/MAD, dan scoring `peer_z`.
* **Hari 3: Opportunity Discovery & Ranking**
  Hitung `discrepancy_z`, sort top kandidat per subsektor, kualifikasi likuiditas pasar, dan verifikasi universe run.
* **Hari 4: Smart Research & Confirmation Layer**
  Sintesis bukti teks via LLM (Mosaic dari Filings, Corporate Actions, Berita) + Confirmation Layer (Foreign Flow & Top Broker direction).
* **Hari 5: Thesis Engine, Numerical Challenge & Memo Output**
  Validasi silang teks vs angka, kompilasi Investment Memo terstruktur (JSON/Markdown), logging discrepancy trace.
* **Hari 6: Frontend UI**
  Dashboard web (Overview Discrepancy Universe, Feed Peluang Emiten, Interactive Investment Memo View).
* **Hari 7: Stress Test, Demo Caching, README & Video Demo**
  Pengujian end-to-end dengan live cache fallback, dokumentasi anti-overfitting di README, dan rekaman video submission.

---

> [!TIP]
> **Kunci Sukses Hackathon**: Jangan mengubah-ubah formula di tengah jalan untuk mencocokkan hasil demo. Kunci rumus matematika Anda di Hari 2 & 3, lalu biarkan sistem menemukan emiten yang benar-benar anomali secara objektif. Integritas inilah yang menjadi kriteria penilaian utama juri.
