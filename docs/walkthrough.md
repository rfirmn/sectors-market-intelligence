# DOKUMENTASI PROGRES PROYEK (PROJECT WALKTHROUGH)
## Market Intelligence Agent — Sectors Hackathon 2026

Dokumen ini mencatat rekam jejak pengerjaan proyek secara lengkap, transparan, dan terstruktur: sampai fase mana sistem telah dibangun, modul apa saja yang sudah tuntas, hasil verifikasi teknis, serta langkah berikutnya yang harus dieksekusi.

---

## 1. Status Proyek Saat Ini (Current Progress Tracker)

* **Fase Berjalan**: **Hari 2 Selesai (100%)** $\longrightarrow$ **Siap Memulai Hari 3**
* **Repository Remote**: [`https://github.com/rfirmn/sectors-market-intelligence.git`](https://github.com/rfirmn/sectors-market-intelligence.git) (Branch `main` ter-sync)
* **Unit Tests Status**: **84 / 84 Tests LULUS (100% Pass Rate, 0 Warnings)**
* **Linter & Type Checker**: `ruff` (0 error) & `pyright` (0 error)
* **Konektivitas Live API**:
  * **Sectors Financial API v2**: **TERVERIFIKASI LIVE** (7 Endpoint lolos uji)
  * **Google Gemini LLM**: **TERVERIFIKASI LIVE** (`gemini-3.5-flash-lite`, 1.8s)
  * **Market State Engine**: **TERVERIFIKASI LIVE** (`make smoke-test-engine` ASII Cross-Check PASS)

### Matriks Progres Sprint 7 Hari

| Fase / Hari | Fokus Utama | Target Deliverable | Status |
|---|---|---|:---:|
| **HARI 1** | **Fondasi, Arsitektur & Integrasi Data** | Setup repo, Client Sectors API, Cache Snapshot, Test Suite, LLM Client | **SELESAI (100%)** |
| **HARI 2** | **Market State Engine & Normalisasi** | Eksklusi Finansial, 8 Metrik Keuangan, Winsorizing 1%/99%, Median/MAD, `peer_z` | **SELESAI (100%)** |
| **HARI 3** | **Discovery Engine & Ranking** | Formula Discrepancy, Threshold 1.0 & 1.5 a priori, Priority Score & Ranking | **BERIKUTNYA (READY)** |
| **HARI 4** | **Smart Research & Confirmation** | Mosaic LLM Evidence (Filings, Actions, News), Net Foreign Flow Direction Check | Menunggu Hari 3 |
| **HARI 5** | **Thesis, Stress Test & Memo** | Thesis Engine, Numerical Challenge (Base/Conservative/Stress), Memo Generator | Menunggu Hari 4 |
| **HARI 6** | **Frontend UI (Dashboard 3 Area)** | Overview Market Scan, Opportunity Feed, Interactive Memo Viewer (FastAPI + SPA) | Menunggu Hari 5 |
| **HARI 7** | **Demo Reliability & Packaging** | Offline fallback test, Final README anti-overfitting, Rekaman Video Demo | Menunggu Hari 6 |

---

## 2. Rincian Pekerjaan yang Telah Diselesaikan (Hari 1)

### A. Setup Lingkungan & Keamanan Secrets (Task T1.1)
1. **Package Management via `uv`**:
   * Seluruh dependensi didefinisikan secara deklaratif di [`pyproject.toml`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/pyproject.toml).
   * Manajemen virtual environment sub-detik (`.venv`).
2. **Keamanan Kredensial**:
   * File [`.gitignore`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/.gitignore) secara ketat memblokir file [`.env`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/.env) agar API Key tidak pernah bocor ke git.
   * Disediakan template [`.env.example`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/.env.example) yang aman untuk publik.
3. **Konfigurasi Terpusat**:
   * [`src/config.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/config.py) menggunakan `pydantic_settings.BaseSettings` untuk memuat variabel lingkungan dengan validasi tipe data yang ketat.

### B. Sectors API Client Adapter (Task T1.2)
1. **HTTP Client Tangguh ([`src/client/sectors_client.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/client/sectors_client.py))**:
   * Header autentikasi `Authorization: {api_key}` sesuai standar resmi Sectors API v2.
   * Retry logic berbasis exponential backoff dengan jitter via `tenacity` untuk menangani status code transien (HTTP 429 dan 5xx).
   * Rate limiting terintegrasi (`sectors_rate_limit_delay`) untuk menjaga frekuensi request tetap sopan.
   * Mendukung pemanggilan sinkron (`request`) dan asinkron (`request_async`).
2. **Pemetaan Error Domain ([`src/client/exceptions.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/client/exceptions.py))**:
   * `AuthenticationError` (401/403), `ResourceNotFoundError` (404), `RateLimitExceededError` (429), `ServerError` (5xx).
3. **Data Contracts Model Pydantic ([`src/client/models.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/client/models.py))**:
   * Model respon disesuaikan secara presisi dengan schema data live Sectors API: `SubsectorInfo`, `CompaniesResponse`, `QuarterlyFinancial`, `DailyTransaction`, `FilingItem`, `CorporateActionItem`, `NewsItem`, dan `ForeignFlowResponse`.

### C. Local Snapshot Cache (§6.10 Demo Reliability Mechanism — Task T1.3)
1. **Arsitektur Cache ([`src/client/cache.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/client/cache.py))**:
   * Setiap response sukses dari Sectors API disimpan ke direktori lokal [`data/cache/sectors/`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/data/cache/sectors/).
   * Penamaan file JSON bersifat deterministik dan mudah dibaca (misal: `subsectors.json`, `financials_quarterly_ASII__n_quarters-4.json`).
   * Setiap file cache menyimpan metadata lengkap (`endpoint`, `params`, `timestamp`, `ttl_hours`).
2. **Fail-Safe Offline Fallback**:
   * Jika saat demo atau pengujian koneksi internet terputus atau terkena rate limit, client secara otomatis membaca snapshot cache terakhir tanpa menyebabkan fatal error (*zero downtime presentation*).

### D. Mesin Linguistik LLM ([`src/research/llm.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/research/llm.py))
* Client Google Gemini ringan berbasis `httpx` langsung ke endpoint REST Generative Language API v1beta (tanpa bloatware SDK).
* Menggunakan model `gemini-3.5-flash-lite` dengan latensi respons sub-2-detik.
* Menangani system instruction dan parameter temperatur untuk sintesis bukti kualitatif.

### E. Arsitektur Domain-Driven & Layer API Server
Struktur modular telah disiapkan untuk mendukung seluruh siklus pipeline hingga frontend:
```
market-intelligence/
├── src/
│   ├── client/         # [Hari 1] Data Ingestion & Snapshot Cache
│   ├── engine/         # [Hari 2] Market State Engine & Stats Normalization
│   ├── discovery/      # [Hari 3] Opportunity Discovery & Priority Ranking
│   ├── research/       # [Hari 4] Smart Research Mosaic (LLM Client)
│   ├── confirmation/   # [Hari 4] Confirmation Layer (Foreign Flow Check)
│   ├── challenge/      # [Hari 5] Numerical Challenge Engine (Deterministic)
│   ├── memo/           # [Hari 5] Investment Memo Synthesizer
│   ├── api/            # [Hari 5-6] FastAPI Server (Serving Endpoints ke UI)
│   └── config.py       # Pydantic Settings
├── frontend/           # [Hari 6] Modern Web UI Dashboard
├── data/cache/sectors/ # File JSON Snapshot Cache
├── scripts/            # CLI Runners (smoke_test.py, smoke_test_llm.py)
├── tests/              # Test suite (15 unit tests)
└── Makefile            # Shortcut developer
```

---

## 3. Bukti Verifikasi & Pengujian Teknis

### A. Live Smoke Test Sectors API v2 (`make smoke-test`)
Pengujian riil terhadap data bursa IDX menggunakan emiten acuan **ASII (Astra International Tbk)**:

```
                  Hasil Pengujian Konektivitas Sectors API v2                   
╭───────────────────┬──────────────────┬────────┬──────────┬───────────────────╮
│ Pipeline Stage    │ Endpoint         │ Status │  Latency │ Payload / Catatan │
├───────────────────┼──────────────────┼────────┼──────────┼───────────────────┤
│ 1. Taxonomy       │ GET              │  PASS  │ 821.6 ms │ 33 subsektor IDX  │
│                   │ /v2/subsectors/  │        │          │ terdaftar         │
│ 1. Screener       │ GET              │  PASS  │ 445.9 ms │ Total 962 emiten  │
│                   │ /v2/companies/?… │        │          │ terindeks         │
│ 2. Financials     │ GET              │  PASS  │ 612.6 ms │ 4 kuartal laba    │
│                   │ /v2/financials/… │        │          │ rugi & neraca     │
│ 3. Daily Quotes   │ GET              │  PASS  │ 422.7 ms │ 20 hari transaksi │
│                   │ /v2/daily/ASII/  │        │          │ OHLCV             │
│ 4. News / Filings │ GET              │  PASS  │ 453.7 ms │ Keterbukaan info  │
│                   │ /v2/filings/?sy… │        │          │ insider/direksi   │
│ 4. News / Filings │ GET              │  PASS  │ 251.9 ms │ Berita terkurasi  │
│                   │ /v2/news/?symbo… │        │          │ pasar modal       │
│ 5. Foreign Flow   │ GET              │  PASS  │ 529.2 ms │ Net aliran dana   │
│                   │ /v2/foreign-flo… │        │          │ investor asing    │
│ Cache Validation  │ Local Cache HIT  │  PASS  │  0.52 ms │ Langsung dari     │
│                   │ test             │        │          │ disk JSON (1000x  │
│                   │ (/v2/subsectors… │        │          │ lebih cepat!)     │
╰───────────────────┴──────────────────┴────────┴──────────┴───────────────────╯
```

### B. Live Smoke Test Google Gemini LLM (`make smoke-test-llm`)
* **Status**: **PASS (200 OK)** dalam **1.8 detik**.
* **Output Sintesis**:
  > **Keunggulan:** PT Astra International Tbk (ASII) memiliki keunggulan kompetitif berupa *monopoli pangsa pasar* otomotif domestik di atas 50% yang ditopang oleh ekosistem rantai pasok yang terintegrasi penuh dari hulu ke hilir.
  >
  > **Risiko:** Risiko utama emiten ini adalah tingginya volatilitas harga komoditas global—khususnya batu bara melalui UNTR—serta potensi perang harga di segmen kendaraan roda empat akibat gempuran pemain EV baru asal Tiongkok.

### C. Automated Unit Test Suite (`make test`)
* **15 dari 15 test LULUS 100%**:
  * `tests/test_api.py`: Endpoint health check dan system status FastAPI.
  * `tests/test_cache.py`: Cache miss, cache set/get, parameter isolation, TTL expiration & offline fallback.
  * `tests/test_sectors_client.py`: Headers autentikasi, cache bypass, error handling (401, 404, 500), network resilience fallback, dan convenience methods.
  * `tests/test_llm.py`: Offline mock parsing respon Gemini.

---

## 4. File Snapshot Cache yang Tersimpan di Disk

Direktori [`data/cache/sectors/`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/data/cache/sectors/) saat ini memuat data riil:
1. `subsectors.json` (3,096 bytes) — Taksonomi seluruh sektor bursa.
2. `companies__limit-5_offset-0.json` (919 bytes) — Cuplikan screener emiten.
3. `financials_quarterly_ASII__n_quarters-4.json` (6,595 bytes) — Laporan laba rugi kuartalan lengkap ASII.
4. `daily_ASII.json` (4,362 bytes) — Data transaksi harian dan market cap.
5. `filings__limit-5_symbol-ASII.json` (8,194 bytes) — Keterbukaan informasi kepemilikan/transaksi orang dalam.
6. `news__limit-5_symbols-ASII.json` (11,804 bytes) — Berita pasar modal terkait ASII.
7. `foreign-flow_ASII.json` (5,715 bytes) — Data net foreign buy/sell harian.

---

## 5. Cheat-sheet Perintah Kerja (Developer Ergonomics)

Gunakan perintah cepat berikut melalui [`Makefile`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/Makefile):

```bash
# Menjalankan seluruh unit test suite (offline)
make test

# Menjalankan live smoke test Sectors API v2
make smoke-test

# Menjalankan live smoke test Gemini LLM
make smoke-test-llm

# Menjalankan server backend FastAPI (port 8000)
make dev-api

# Pengecekan linter dan tipe data
make lint

# Merapikan formatting kode otomatis
make format
```

---

## 6. Rincian Pekerjaan yang Telah Diselesaikan (Hari 2)

### A. Data Contracts & Models (`src/engine/models.py`)
* `MetricSet`: Representasi 8 metrik finansial mentah (`revenue_growth`, `earnings_growth`, `operating_margin`, `margin_change`, `roe_ttm`, `price_return`, `pe_ttm`, `pb`).
* `PeerZScores`: Representasi skor z-score peer-normalized subsektor.
* `CompanyState`: Struktur agregasi final per emiten dengan provenance lengkap (`growth_period`, `growth_method`, `price_period`, `data_timestamp`).
* `SubsectorProfile` & `MetricDistribution`: Metadata statistik subsektor (median, MAD, scaled_MAD, bounds persentil 1%/99%, n_valid, flag winsorized).

### B. Robust Statistics Engine (`src/engine/stats.py`)
* Implementasi pure-Python tanpa ketergantungan numpy/scipy:
  * Linear interpolation percentile.
  * Winsorizing persentil 1% & 99% (guard sample minimum $n \ge 5$).
  * Median & MAD (Median Absolute Deviation) dengan consistency factor $k = 1.4826$ (Iglewicz & Hoaglin 1993) agar $1.4826 \times \text{MAD}$ menjadi estimator robust dari $\sigma$.
  * Fallback scale saat $\text{MAD} = 0$: $0.01 \times |\text{median}|$ untuk menghindari pembagian dengan nol.
  * Guard sample kecil ($n < 3$ menghasilkan $z = 0.0$ konservatif).

### C. Taxonomy & Universe Builder (`src/engine/taxonomy.py`)
* Filter ketat eksklusi sektor finansial (`financials`: perbankan, asuransi, pembiayaan) sesuai spesifikasi §6.1.
* Stripping otomatis suffix `.JK` dari ticker screener (`ASII.JK` $\to$ `ASII`).
* Pagination handling untuk query subsektor perusahaan.

### D. Financial Metrics Calculator (`src/engine/metrics.py`)
* Strategi pertumbuhan adaptif: YoY jika tersedia data pembanding 4 kuartal sebelumnya, fallback mulus ke QoQ jika data terbatas.
* TTM Aggregation: ROE dan PE dihitung berbasis akumulasi laba 4 kuartal berjalan (TTM) dibagi ekuitas terkini.
* Penanganan komprehensif edge case numerik: denominator nol, laba rugi berbalik (loss-to-profit), ekuitas negatif, dan observasi harga minim.

### E. Pipeline Orchestrator & Smoke Test Engine (`src/engine/market_state_engine.py`)
* Mengintegrasikan rantai Taksonomi $\to$ Data Fetching $\to$ Kalkulasi Metrik $\to$ Normalisasi Subsektor.
* Verifikasi cross-check numerik ASII (`make smoke-test-engine`):
  * Revenue Growth (QoQ): `+0.73%` (Cocok)
  * Earnings Growth (QoQ): `+14.24%` (Cocok)
  * Operating Margin: `10.23%` (Cocok)
  * Margin Change: `+2.21 pp` (Cocok)
  * ROE TTM: `10.28%` (Cocok)
  * PE TTM: `6.67x` (Cocok)
  * All Peer Z-scores: `0.0000` (Kompak sesuai teori n=1)

> [!NOTE]
> Dokumentasi lengkap arsitektur sistem, rasionalitas bisnis/finansial, penurunan rumus matematika konsistensi MAD ($k=1.4826$), dan pembuktian formal invarian telah didokumentasikan di [`docs/engine_mathematics_and_logic.md`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs/engine_mathematics_and_logic.md).

---

## 7. Rencana Kerja Selanjutnya: HARI 3

Fokus berikutnya adalah **Opportunity Discovery, Ranking & Pengujian Universe**:

* **Task T3.1**: Implementasi penghitungan `fundamental_z` (rata-rata z-score pertumbuhan pendapatan, laba, dan perubahan margin) dan `price_z`.
* **Task T3.2**: Implementasi aturan discrepancy: $\text{discrepancy} = \text{fundamental\_z} - \text{price\_z}$ dan klasifikasi a priori:
  * $\text{discrepancy} > 1.5 \longrightarrow$ **HIGH Priority**
  * $1.0 < \text{discrepancy} \le 1.5 \longrightarrow$ **MEDIUM Priority**
  * $\text{discrepancy} \le 1.0 \longrightarrow$ Filtered out / non-candidate
* **Task T3.3**: Priority Score & Ranking Engine untuk memilih top kandidat peluang pasar modal.
* **Task T3.4**: Penguncian parameter matematis a priori di dokumentasi/README.
* **Task T3.5**: Scan universe non-finansial IDX untuk menemukan 2–3 emiten riil dengan dislokasi harga nyata.
