# 03. TRANSAKSI HARIAN, INDEKS & RANKING IDX
## Sectors Financial API v2.0.0

Modul ini mendokumentasikan endpoint pergerakan harga pasar, transaksi harian historis, feed harga penutupan seluruh emiten bursa (*Full-Universe Close*), indeks pasar (IHSG, LQ45, IDX30), kapitalisasi total pasar, serta ranking pergerakan saham (*Top Movers*, *Most Traded*, dan *IPO Performance*).

---

## 1. Daily Transaction Data (`/v2/daily/{symbol}/`)

Mengembalikan data harga harian (OHLCV) dan kapitalisasi pasar untuk satu simbol IDX dalam rentang waktu hingga 90 hari.

* **Endpoint**: `GET /v2/daily/{symbol}/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Path & Query:
| Parameter | Tipe | Lokasi | Wajib? | Deskripsi |
|---|---|---|---|---|
| `symbol` | String | Path | **Ya** | Kode emiten IDX (misal: `BBCA`, `GOTO`, `TLKM`). |
| `start` | String | Query | Opsional | Tanggal awal `YYYY-MM-DD`. Default: 30 hari sebelum `end`. |
| `end` | String | Query | Opsional | Tanggal akhir `YYYY-MM-DD`. Default: Hari ini. |

### Contoh Respon JSON:
```json
[
  {
    "symbol": "BBCA.JK",
    "date": "2025-05-02",
    "open": 9000,
    "high": 9000,
    "low": 8850,
    "close": 8975,
    "volume": 92219000,
    "market_cap": 1095329638012500
  }
]
```

---

## 2. Daily Full-Universe Close (`/v2/close/`)

Mengembalikan harga penutupan seluruh emiten bursa IDX (~900+ saham) pada satu tanggal perdagangan tertentu dalam satu feed terpaginasi. Endpoint ini sangat efisien untuk menghitung *market state* atau *cross-sectional price return* tanpa memanggil endpoint per ticker satu per satu.

* **Endpoint**: `GET /v2/close/`
* **Metode**: `GET`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `date` | String | Opsional | Tanggal perdagangan `YYYY-MM-DD`. Default: Hari bursa terakhir. |
| `limit` | Integer | Opsional | Maksimal emiten per halaman. Default: 30, Maksimal: 100. |
| `offset` | Integer | Opsional | Offset untuk paginasi. |

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "symbol": "AADI.JK",
      "date": "2025-05-02",
      "close": 7150
    },
    {
      "symbol": "AAID.JK",
      "date": "2025-05-02",
      "close": 125
    }
  ],
  "pagination": {
    "total_count": 942,
    "showing": 2,
    "limit": 30,
    "offset": 0,
    "has_next": true,
    "has_previous": false,
    "next_offset": 30,
    "previous_offset": null
  }
}
```

---

## 3. Total Kapitalisasi Pasar IDX (`/v2/idx-total/`)

Mengembalikan data historis kapitalisasi pasar gabungan seluruh Bursa Efek Indonesia dalam rentang hingga 90 hari.

* **Endpoint**: `GET /v2/idx-total/`
* **Parameter Query**: `start` (string YYYY-MM-DD), `end` (string YYYY-MM-DD).

---

## 4. Indeks Saham Harian (`/v2/index-daily/{index_code}/`)

Mengembalikan pergerakan nilai indeks acuan pasar modal Indonesia (misal: IHSG, LQ45, IDX30, IDXHIDIV20).

* **Endpoint**: `GET /v2/index-daily/{index_code}/`
* **Parameter Path**: `index_code` (string, contoh: `ihsg`, `lq45`, `idx30`, `kompas100`).
* **Parameter Query**: `start` (string YYYY-MM-DD), `end` (string YYYY-MM-DD).
* **Contoh Respon**: Array data tanggal dan closing value indeks.

---

## 5. Top Company Movers (`/v2/companies/top-changes/`)

Mengembalikan daftar saham dengan kenaikan (*top gainers*) dan penurunan (*top losers*) paling signifikan pada berbagai horizon waktu (`1d`, `7d`, `14d`, `30d`, `365d`).

* **Endpoint**: `GET /v2/companies/top-changes/`
* **Metode**: `GET`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `sub_sector` | String | Opsional | Filter berdasarkan subsektor spesifik (kebab-case). |
| `classifications` | Array | Opsional | `top_gainers` atau `top_losers`. |
| `periods` | Array | Opsional | Pilihan periode: `1d`, `7d`, `14d`, `30d`, `365d`. |
| `n_stock` | Integer | Opsional | Jumlah saham per periode (default: 5, max: 10). |
| `min_mcap_billion` | Integer | Opsional | Filter minimum market cap (miliar IDR) untuk menyaring saham non-likuid. |

### Contoh Respon JSON:
```json
{
  "top_gainers": {
    "1d": [
      {
        "name": "PT Astra International Tbk",
        "symbol": "ASII.JK",
        "price_change": 0.045,
        "last_close_price": 5200,
        "latest_close_date": "2026-07-08"
      }
    ],
    "7d": [ ... ]
  },
  "top_losers": {
    "1d": [ ... ]
  }
}
```

---

## 6. Saham Paling Aktif Diperdagangkan (`/v2/most-traded/`)

Menyajikan saham-saham paling likuid di bursa berdasarkan volume transaksi atau nilai transaksi per hari.

* **Endpoint**: `GET /v2/most-traded/`
* **Parameter Query**:
  * `sub_sector`: Filter subsektor spesifik.
  * `start`, `end`: Rentang tanggal (maks 90 hari).
  * `adjusted`: Boolean. Jika `true`, peringkat didasarkan pada Nilai Transaksi (Volume × Harga Penutupan), bukan hanya lembar saham.
  * `n_stock`: Jumlah emiten per hari (default 5, max 10).

---

## 7. Kinerja Pasca IPO (`/v2/listing-performance/{symbol}/`)

Mengukur performa harga saham sejak tanggal pencatatan perdana (*IPO listing date*) pada horizon 7, 30, 90, dan 365 hari.

* **Endpoint**: `GET /v2/listing-performance/{symbol}/`
* **Parameter Path**: `symbol` (misal: `BREN`, `GOTO`, `ARTO`).
* **Respon**: Tanggal IPO, harga penawaran perdana, serta persentase perubahan harga pada masing-masing jendela waktu.
