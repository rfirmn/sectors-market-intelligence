# SECTORS FINANCIAL API — DOKUMENTASI LENGKAP & SISTEMATIS
## Versi API: v2.0.0 | Base URL: `https://api.sectors.app/v2/`

Selamat datang di repositori dokumentasi teknis **Sectors Financial API v2**. Dokumentasi ini disusun secara modular untuk mempermudah navigasi pengembang, analisis data finansial, serta integrasi AI Agent pada ekosistem pasar modal Indonesia (IDX) dan regional (SGX & KLSE).

---

## Daftar Berkas Dokumentasi

Dokumentasi ini dipecah ke dalam berkas-berkas tematik sesuai domain fungsinya:

| File | Judul / Topik | Cakupan Utama |
|---|---|---|
| [00_overview_and_auth.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/00_overview_and_auth.md) | **Arsitektur, Autentikasi & Konvensi** | Base URL, Header `Authorization`, Status Code, Rate Limits, Pagination (`limit`/`offset`), dan query syntax (`where`/`q`). |
| [01_idx_screener_and_taxonomy.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/01_idx_screener_and_taxonomy.md) | **Taksonomi, Screener & Free Float IDX** | Helper lists (subsectors, industries, subindustries, tags), compound SQL screener, NLP screener, dan free float universe. |
| [02_idx_financials_and_reports.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/02_idx_financials_and_reports.md) | **Laporan Keuangan & Fundamental IDX** | Quarterly financials per emiten, universe report dates, company reports, subsector reports, corporate actions, shareholders, & segments. |
| [03_idx_transactions_and_rankings.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/03_idx_transactions_and_rankings.md) | **Transaksi Harian, Indeks & Ranking IDX** | Daily OHLCV & Market Cap, full-universe close single-day feed, IHSG/index history, top gainers/losers, most traded, dan IPO performance. |
| [04_idx_news_filings_and_suspensions.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/04_idx_news_filings_and_suspensions.md) | **News, Filings & Suspensi Saham IDX** | Transaksi insider trading / pemegang saham mayoritas, artikel berita bursa terkurasi, serta riwayat suspensi emiten oleh BEI. |
| [05_idx_brokers_and_foreign_flow.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/05_idx_brokers_and_foreign_flow.md) | **Broker Summary & Foreign Flow IDX** | Daily net foreign inflow per emiten, registri broker terkurasi (kode, origin, cohort), top akumulasi/distribusi, dan broker summary per emiten. |
| [06_sgx_singapore_market.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/06_sgx_singapore_market.md) | **Pasar Singapura (SGX)** | Screener emiten SGX, laporan perusahaan, buybacks, transaksi harian, short sell, insider filings, dan berita SGX. |
| [07_klse_malaysia_market.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/07_klse_malaysia_market.md) | **Pasar Malaysia (KLSE)** | Daftar emiten per sektor KLSE, ranking perusahaan, profil emiten, dan taksonomi sektor Bursa Malaysia. |
| [08_mining_specialized_data.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/08_mining_specialized_data.md) | **Spesialisasi Sektor Pertambangan RI** | Data operasional tambang ESDM/Minerba: profil operasional, kepemilikan, komoditas & harga, ekspor, lokasi tambang, cadangan & lelang izin (WIUP/IUP). |
| [09_hackathon_pipeline_mapping.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/docs_sectors_api/09_hackathon_pipeline_mapping.md) | **Pemetaan Pipeline Market Intelligence Agent** | Panduan integrasi langsung endpoint Sectors ke loop `NUMERICAL → LINGUISTIC → NUMERICAL` proyek MVP Hackathon 2026. |

---

## Ringkasan Cakupan Endpoint (70 Endpoints)

```
Sectors API v2.0.0
├── Indonesia (IDX Core)
│   ├── Helper Lists & Taxonomy (7 endpoints)
│   ├── Screener & Free Float (2 endpoints)
│   ├── Reports & Financials (8 endpoints)
│   ├── Transactions & Rankings (7 endpoints)
│   ├── News, Filings & Suspensions (3 endpoints)
│   └── Brokers & Foreign Flow (7 endpoints)
├── Indonesia Specialized
│   └── Mining & Resources - ESDM (19 endpoints)
├── Singapore (SGX)
│   └── Screener, Reports, Transactions, Filings (12 endpoints)
└── Malaysia (KLSE)
    └── Sectors, Companies, Reports, Rankings (5 endpoints)
```

Silakan buka masing-masing berkas di atas untuk membaca spesifikasi parameter lengkap, URL path, contoh response JSON, dan implementasi kode.
