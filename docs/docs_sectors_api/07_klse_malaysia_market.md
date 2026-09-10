# 07. PASAR MALAYSIA (KLSE)
## Sectors Financial API v2.0.0

Sectors Financial API menyediakan integrasi data fundamental dan ringkasan emiten untuk Bursa Malaysia (Kuala Lumpur Stock Exchange / KLSE). Modul ini mendokumentasikan taksonomi sektor, penyaringan emiten, peringkat emiten, dan laporan komprehensif perusahaan KLSE.

---

## 1. Konvensi Simbol KLSE

* **Format Simbol**: Kode numerik 4 digit (misal: `1155` untuk Malayan Banking / Maybank, `5225` untuk IHH Healthcare, `1295` untuk Public Bank).
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

---

## 2. Taksonomi Sektor KLSE (`/v2/klse/sectors/`)

Mengembalikan seluruh slug sektor industri yang terdaftar di Bursa Malaysia.

* **Endpoint**: `GET /v2/klse/sectors/`
* **Metode**: `GET`
* **Contoh Respon JSON**:
```json
[
  "consumer-products-services",
  "financial-services",
  "industrial-products-services",
  "plantation",
  "technology",
  "telecommunications-media"
]
```

---

## 3. Daftar Emiten per Sektor KLSE (`/v2/klse/companies/`)

Mengembalikan seluruh emiten yang tergabung dalam suatu sektor industri di KLSE.

* **Endpoint**: `GET /v2/klse/companies/`
* **Parameter Query**: `sector` (Wajib, string kebab-case, misal: `financial-services`).
* **Contoh Respon JSON**:
```json
[
  {
    "symbol": "1155",
    "company_name": "Malayan Banking Berhad"
  },
  {
    "symbol": "1295",
    "company_name": "Public Bank Berhad"
  }
]
```

---

## 4. Peringkat Emiten KLSE (`/v2/klse/companies/top/`)

Peringkat emiten teratas di Bursa Malaysia berdasarkan satu atau lebih klasifikasi finansial: `market_cap`, `dividend_yield`, `revenue`, `earnings`, atau `pe`.

* **Endpoint**: `GET /v2/klse/companies/top/`
* **Parameter Query**:
  * `classifications`: Array string klasifikasi.
  * `n_stock`: Jumlah emiten yang dikembalikan per klasifikasi.

---

## 5. Full Company Report KLSE (`/v2/klse/company/report/{symbol}/`)

Laporan mendalam performa keuangan, rasio valuasi, dividen, dan profil emiten KLSE.

* **Endpoint**: `GET /v2/klse/company/report/{symbol}/`
* **Parameter Path**: `symbol` (Kode 4 digit numerik, misal: `1155`).
* **Parameter Query**: `sections` (Array string: `overview`, `valuation`, `financials`, `dividend`, `management`, `peers`).
