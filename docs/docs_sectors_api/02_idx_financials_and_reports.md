# 02. LAPORAN KEUANGAN & FUNDAMENTAL IDX
## Sectors Financial API v2.0.0

Modul ini mendokumentasikan endpoint fundamental emiten IDX: laporan keuangan kuartalan historis (*Quarterly Financials*), helper tanggal laporan bursa, ringkasan komprehensif emiten (*Company Report*), laporan agregat subsektor (*Subsector Report*), aksi korporasi (*Corporate Actions*), komposisi pemegang saham (*Shareholders Composition*), dan segmentasi pendapatan (*Revenue Segments*).

---

## 1. Company Quarterly Financials (`/v2/financials/quarterly/{symbol}/`)

Mengembalikan data laporan keuangan kuartalan historis (Neraca, Laba Rugi, Arus Kas) untuk emiten tertentu.

* **Endpoint**: `GET /v2/financials/quarterly/{symbol}/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Path & Query:
| Parameter | Tipe | Lokasi | Wajib? | Deskripsi |
|---|---|---|---|---|
| `symbol` | String | Path | **Ya** | Kode emiten IDX (misal: `BBCA`, `ASII`, `TLKM`). |
| `n_quarters` | Integer | Query | Opsional | Jumlah kuartal terbaru yang ingin diambil (misal: `4` untuk 4 kuartal terakhir). |
| `report_date` | String | Query | Opsional | Tanggal laporan spesifik dalam format `YYYY-MM-DD`. |
| `approx` | Boolean | Query | Opsional | Default `true`. Mengizinkan pencocokan kuartal terdekat jika tanggal persis tidak ada. |

### Karakteristik Struktur Data (Non-Finansial vs Finansial):
* **Emiten Non-Finansial (Manufaktur, Energi, Konsumer, Teknologi, dll.)**:
  Memiliki metrik standar: `revenue`, `cost_of_revenue`, `gross_profit`, `operating_pnl`, `ebit`, `ebitda`, `earnings` (net profit), `total_assets`, `total_liabilities`, `total_equity`, `operating_cash_flow`, `free_cash_flow`.
* **Emiten Finansial (Bank, Asuransi, Multifinance)**:
  Memiliki blok khusus `financials_sector_metrics` yang memuat: `interest_income`, `interest_expense`, `net_interest_income`, `gross_loan`, `allowance_for_loans`, `net_loan`, `total_deposit`.
  *(Catatan: Sektor finansial dikecualikan dari engine discovery sesuai §6.1 `project.md`)*.

### Contoh Respon JSON:
```json
[
  {
    "symbol": "ASII.JK",
    "date": "2025-09-30",
    "revenue": 82450000000000,
    "cost_of_revenue": 65120000000000,
    "gross_profit": 17330000000000,
    "operating_pnl": 11200000000000,
    "ebit": 11200000000000,
    "ebitda": 14500000000000,
    "earnings": 8750000000000,
    "total_assets": 450120000000000,
    "total_liabilities": 210050000000000,
    "total_equity": 240070000000000,
    "operating_cash_flow": 12400000000000,
    "free_cash_flow": 9100000000000
  }
]
```

---

## 2. Helper Tanggal Laporan Kuartalan

Untuk mengetahui tanggal pelaporan kuartal yang valid sebelum memanggil laporan keuangan:

### 2.1 Universe Latest Quarterly Dates (`/v2/companies/quarterly-financial-dates/`)
* **Endpoint**: `GET /v2/companies/quarterly-financial-dates/`
* **Deskripsi**: Mengembalikan tanggal laporan kuartal terbaru untuk seluruh emiten IDX dalam satu feed terpaginasi (menghindari pemanggilan per emiten).
* **Parameter Query**: `year` (int), `since` (string YYYY-MM-DD), `limit` (int, max 100), `offset` (int).

### 2.2 Company Quarterly Financial Dates (`/v2/company/get_quarterly_financial_dates/{symbol}/`)
* **Endpoint**: `GET /v2/company/get_quarterly_financial_dates/{symbol}/`
* **Deskripsi**: Daftar seluruh tanggal laporan keuangan kuartalan yang tersedia untuk satu simbol, dikelompokkan per tahun.

---

## 3. Company Comprehensive Report (`/v2/company/report/{symbol}/`)

Mengembalikan laporan 360 derajat suatu emiten yang mencakup profil bisnis, valuasi, rasio pertumbuhan, deviden, dan perbandingan industri.

* **Endpoint**: `GET /v2/company/report/{symbol}/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`
* **Parameter Query**: `sections` (Array string). Pilihan section:
  * `overview`: Profil perusahaan, deskripsi bisnis, kapitalisasi pasar.
  * `valuation`: PE, PB, EV/EBITDA, PS ratio historis dan relatif.
  * `financials`: Ringkasan neraca, laba rugi, dan arus kas multi-tahun.
  * `dividend`: Riwayat yield dan dividend payout ratio.
  * `management`: Jajaran direksi dan komisaris.
  * `peers`: Emiten sebanding di subsektor yang sama.

---

## 4. Subsector Aggregate Report (`/v2/subsector/report/{sub_sector}/`)

Mengembalikan analisis statistik agregat untuk suatu subsektor di bursa IDX. Sangat berguna untuk benchmarking intra-industry.

* **Endpoint**: `GET /v2/subsector/report/{sub_sector}/`
* **Parameter Path**: `sub_sector` (kebab-case, misal: `banks`, `metals-mining`, `telecommunication`).
* **Parameter Query**: `sections` (Array string).

---

## 5. Corporate Actions (`/v2/company/corporate-actions/{symbol}/`)

Mengembalikan riwayat aksi korporasi emiten: pembagian dividen (kumulatif & interim), pemecahan saham (*stock split*), *rights issue*, dan *warrant*.

* **Endpoint**: `GET /v2/company/corporate-actions/{symbol}/`
* **Metode**: `GET`
* **Contoh Respon JSON**:
```json
[
  {
    "symbol": "BBCA.JK",
    "action_type": "dividend",
    "cum_date": "2025-11-20",
    "ex_date": "2025-11-21",
    "recording_date": "2025-11-24",
    "payment_date": "2025-12-10",
    "amount": 55.0,
    "currency": "IDR"
  }
]
```

---

## 6. Shareholders Composition (`/v2/company/shareholders-composition/{symbol}/`)

Menampilkan struktur kepemilikan saham terkini dan historis per tahun kalender.

* **Endpoint**: `GET /v2/company/shareholders-composition/{symbol}/`
* **Parameter Query**: `year` (int, default tahun berjalan).
* **Komponen Data**:
  * Pengendali (*Controlling Shareholder*) & Persentase.
  * Pemegang saham di atas 5%.
  * Kepemilikan Direksi & Komisaris.
  * Kepemilikan Publik / Ritel.

---

## 7. Segmentasi Pendapatan & Biaya (Sankey Graph Data)

### 7.1 List Emiten dengan Segmentasi:
* **Endpoint**: `GET /v2/companies/list_companies_with_segments/`
* **Deskripsi**: Daftar seluruh emiten yang memiliki rincian segmen bisnis beserta tahun yang tersedia.

### 7.2 Rincian Segmen Perusahaan:
* **Endpoint**: `GET /v2/company/get-segments/{symbol}/`
* **Parameter**: `financial_year` (int, misal: `2024`).
* **Format**: Struktur siap-pakai untuk diagram Sankey (Revenue streams → Operating costs → Net income).
