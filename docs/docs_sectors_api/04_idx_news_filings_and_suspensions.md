# 04. BERITA, FILINGS & SUSPENSI SAHAM IDX
## Sectors Financial API v2.0.0

Modul ini mendokumentasikan endpoint kualitatif bursa: transaksi kepemilikan orang dalam (*Company Filings / Insider Trading*), artikel berita pasar terkurasi (*News Articles*), dan riwayat suspensi perdagangan saham oleh bursa (*Stock Suspensions*). Endpoint ini menjadi pilar utama penyusun **Mosaic Evidence** pada pipeline Smart Research (§6.4 `project.md`).

---

## 1. Company Filings — Insider Trading (`/v2/filings/`)

Mengembalikan laporan keterbukaan transaksi efek oleh *insider* (direksi, komisaris, atau pemegang saham utama di atas 5%). Sumber data ini sangat krusial untuk mengonfirmasi apakah manajemen memiliki keyakinan terhadap masa depan perusahaan (*skin in the game*).

* **Endpoint**: `GET /v2/filings/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `symbol` | String | Opsional | Filter berdasarkan kode saham (misal: `BBCA`, `NSSS`). |
| `sector` | String | Opsional | Filter berdasarkan sektor (kebab-case). |
| `sub_sector` | String | Opsional | Filter berdasarkan subsektor (kebab-case). |
| `transaction_type` | String | Opsional | Pilihan: `buy`, `sell`, atau `others`. |
| `holder_type` | String | Opsional | Tipe pemegang saham (misal: `director`, `commissioner`, `institution`). |
| `tags` | String | Opsional | Koma-terpisah tag slug (misal: `Bullish,insider-trading`). |
| `start`, `end` | String | Opsional | Rentang tanggal laporan `YYYY-MM-DD`. |
| `limit` | Integer | Opsional | Jumlah item per halaman (Maksimal: 30). |
| `offset` | Integer | Opsional | Offset untuk paginasi. |

### Contoh Request:
```bash
curl -X GET "https://api.sectors.app/v2/filings/?symbol=NSSS&transaction_type=buy&limit=5" \
     -H "Authorization: $SECTORS_API_KEY"
```

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "symbol": "NSSS.JK",
      "company_name": "Nusantara Sawit Sejahtera Tbk",
      "title": "Samuel Sekuritas Indonesia buys shares of Nusantara Sawit Sejahtera",
      "body": "Samuel Sekuritas Indonesia reported an insider purchase of 15,000,000 shares at IDR 185 per share.",
      "date": "2026-06-15",
      "transaction_type": "buy",
      "holder_name": "Samuel Sekuritas Indonesia",
      "holder_type": "institution",
      "shares_traded": 15000000,
      "price_per_share": 185,
      "tags": ["insider-trading", "Bullish"]
    }
  ],
  "pagination": {
    "total_count": 12,
    "limit": 5,
    "offset": 0,
    "has_next": true
  }
}
```

---

## 2. News Articles (`/v2/news/`)

Mengembalikan artikel berita pasar modal terkurasi dari bursa (IDX) dan sumber berita sektor pertambangan.

* **Endpoint**: `GET /v2/news/`
* **Metode**: `GET`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `extension` | String | Opsional | Pilihan sumber data: `idx` (default bursa umum) atau `mining`. |
| `symbols` | String | Opsional | Koma-terpisah simbol IDX (misal: `BBCA,BBRI`). Hanya untuk extension `idx`. |
| `keyword` | String | Opsional | Pencarian substring judul artikel secara *case-insensitive*. |
| `sector`, `sub_sector` | String | Opsional | Filter berdasarkan taksonomi bursa (kebab-case). |
| `commodity_type` | String | Opsional | Khusus `extension=mining` (misal: `Coal`, `Nickel`, `Gold`). |
| `tags` | String | Opsional | Filter tag bursa (diambil dari `/v2/tags/`). |
| `start`, `end` | String | Opsional | Rentang tanggal publikasi berita `YYYY-MM-DD`. |
| `limit` | Integer | Opsional | Jumlah berita per halaman (Maksimal: 30). |
| `offset` | Integer | Opsional | Offset untuk paginasi. |

### Contoh Request:
```bash
curl -X GET "https://api.sectors.app/v2/news/?symbols=ASII&limit=3" \
     -H "Authorization: $SECTORS_API_KEY"
```

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "title": "Astra International reports Q2 operating margin expansion amid EV diversification",
      "body": "PT Astra International Tbk (ASII) recorded a solid improvement in its automotive and mining contracting margins...",
      "source": "IDX Press Release",
      "date": "2026-07-28",
      "symbols": ["ASII.JK"],
      "tags": ["earnings", "margin-expansion"]
    }
  ],
  "pagination": {
    "total_count": 45,
    "limit": 3,
    "offset": 0,
    "has_next": true
  }
}
```

---

## 3. Stock Suspensions (`/v2/suspensions/`)

Mengembalikan riwayat suspensi perdagangan saham oleh otoritas Bursa Efek Indonesia (BEI), mencakup tanggal gembok suspensi, alasan resmi (misal: *Unusual Market Activity* / UMA, penurunan harga kumulatif, keterlambatan laporan), dan tautan ke surat edaran PDF resmi BEI.

* **Endpoint**: `GET /v2/suspensions/`
* **Metode**: `GET`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `symbol` | String | Opsional | Filter kode emiten (misal: `FLMC`, `GOTO`). |
| `start`, `end` | String | Opsional | Rentang tanggal suspensi `YYYY-MM-DD`. |
| `limit` | Integer | Opsional | Jumlah item per halaman (Maksimal: 30). |
| `offset` | Integer | Opsional | Offset untuk paginasi. |

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "symbol": "FLMC.JK",
      "company_name": "PT Falmaco Nonwoven Industri Tbk",
      "suspension_date": "2026-07-03",
      "reason": "Terjadinya penurunan harga kumulatif yang signifikan pada saham FLMC.JK",
      "pdf_url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202607/Peng-SPT-00042.pdf"
    }
  ],
  "pagination": {
    "total_count": 1,
    "limit": 30,
    "offset": 0
  }
}
```
