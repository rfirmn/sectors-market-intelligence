# 06. PASAR SINGAPURA (SGX)
## Sectors Financial API v2.0.0

Sectors Financial API menyediakan cakupan data komprehensif untuk Bursa Efek Singapura (Singapore Exchange / SGX). Modul ini mendokumentasikan taksonomi, screener, laporan emiten, transaksi harian, aksi *share buyback*, posisi *short sell*, serta filings dan berita pasar SGX.

---

## 1. Konvensi Simbol SGX

* **Format Simbol**: 3–4 karakter alfanumerik (huruf atau angka), secara opsional diikuti oleh suffix `.SI` (misal: `D05` untuk DBS Group, `U11` untuk UOB, `Z74` untuk Singtel).
* **Output Respon**: Selalu mengembalikan kode dengan suffix `.SI` (misal: `D05.SI`).

---

## 2. Taksonomi & Helper Lists SGX

* **List SGX Sectors**: `GET /v2/sgx/sectors/`
  * Mengembalikan array flat slug sektor di SGX.
* **List SGX Subsectors**: `GET /v2/sgx/subsectors/`
  * Mengembalikan pasangan `sector` dan `sub_sector` dalam format kebab-case.
* **List SGX News Tags**: `GET /v2/sgx/tags/`
  * Mengembalikan tag tematik artikel berita dan filings SGX.

---

## 3. SGX Companies Screener (`/v2/sgx/companies/`)

Menyaring dan mengurutkan seluruh emiten yang tercatat di SGX. Mendukung filter SQL-like dan NLP query.

* **Endpoint**: `GET /v2/sgx/companies/`
* **Metode**: `GET`
* **Parameter Query**: `where`, `order_by`, `desc`, `limit`, `offset`, `include_query_values`, `q`.

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "symbol": "D05.SI",
      "company_name": "DBS Group Holdings Ltd",
      "query_values": {
        "sub_sector": "banks",
        "market_cap": 98500000000,
        "dividend_yield": 0.058
      }
    }
  ]
}
```

---

## 4. Full Company Report SGX (`/v2/sgx/company/report/{symbol}/`)

Laporan mendalam perusahaan SGX mencakup fundamental multi-tahun, valuasi, rasio keuangan, dan manajemen.

* **Endpoint**: `GET /v2/sgx/company/report/{symbol}/`
* **Parameter Path**: `symbol` (misal: `D05`, `U11`, `Z74`).
* **Parameter Query**: `sections` (Array: `overview`, `valuation`, `financials`, `dividend`, `management`, `peers`).

---

## 5. Transaksi & Aktivitas Pasar SGX

### 5.1 SGX Daily Price Data (`/v2/sgx/daily/{symbol}/`)
* Mengembalikan data OHLCV harian emiten SGX dalam rentang hingga 90 hari.

### 5.2 SGX Share Buybacks (`/v2/sgx/buybacks/`)
* **Endpoint**: `GET /v2/sgx/buybacks/`
* **Deskripsi**: Riwayat pembelian kembali saham oleh emiten SGX (*share buyback*). Menyajikan tanggal pembelian, tipe buyback, rentang harga pelaksanaan, total nilai, total lembar saham yang dibeli, serta akumulasi saham treasuri (*treasury shares*).
* **Parameter**: `symbol`, `start`, `end`, `limit`, `offset`.

### 5.3 SGX Short Sell (`/v2/sgx/short-sell/`)
* **Endpoint**: `GET /v2/sgx/short-sell/`
* **Deskripsi**: Data volume dan nilai transaksi penjualan kosong (*short selling*) emiten SGX yang dilaporkan secara resmi ke bursa.
* **Parameter**: `symbol`, `start`, `end`.

### 5.4 Top SGX Companies by Classification (`/v2/sgx/companies/top/`)
* Peringkat emiten SGX berdasarkan metrik kinerja: kapitalisasi pasar, dividend yield, pertumbuhan pendapatan, atau valuasi PE.

---

## 6. News & Filings Pasar SGX

* **SGX Insider Filings**: `GET /v2/sgx/filings/`
  * Transaksi jual/beli oleh orang dalam (*insiders*) dan pemegang saham substansial di SGX.
  * Parameter: `symbol`, `transaction_type`, `holder_type`, `start`, `end`.
* **SGX News Articles**: `GET /v2/sgx/news/`
  * Berita terkini mengenai emiten dan pasar modal Singapura.
  * Parameter: `sector`, `sub_sector`, `tags`, `symbols`, `start`, `end`.
