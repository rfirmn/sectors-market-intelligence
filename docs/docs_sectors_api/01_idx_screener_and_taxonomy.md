# 01. TAKSONOMI, SCREENER & FREE FLOAT IDX
## Sectors Financial API v2.0.0

Modul ini mendokumentasikan endpoint pembantu klasifikasi pasar modal Indonesia (taksonomi sektor, industri, subindustri, tag berita), mesin pencarian komprehensif emiten (*Companies Screener*), dan analisis kepemilikan publik (*Free Float*).

---

## 1. Helper Lists — Taksonomi Pasar IDX

Sectors menggunakan klasifikasi hierarkis bursa dalam format `kebab-case`:
`Sector` → `Subsector` → `Industry` → `Subindustry`.

### 1.1 List Subsectors
* **Endpoint**: `GET /v2/subsectors/`
* **Deskripsi**: Mengembalikan seluruh pasangan sektor dan subsektor yang terdaftar di IDX.
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`
* **Parameter**: Tidak ada.
* **Contoh Respon (200 OK)**:
```json
[
  {
    "sector": "financials",
    "subsector": "banks"
  },
  {
    "sector": "basic-materials",
    "subsector": "metals-mining"
  },
  {
    "sector": "consumer-cyclicals",
    "subsector": "apparel-luxury-goods"
  },
  {
    "sector": "technology",
    "subsector": "software-it-services"
  }
]
```

### 1.2 List Industries
* **Endpoint**: `GET /v2/industries/`
* **Deskripsi**: Mengembalikan seluruh pasangan subsektor dan industri dalam format slug.
* **Contoh Respon (200 OK)**:
```json
[
  {
    "subsector": "banks",
    "industry": "banks"
  },
  {
    "subsector": "metals-mining",
    "industry": "copper"
  },
  {
    "subsector": "metals-mining",
    "industry": "gold"
  }
]
```

### 1.3 List Subindustries
* **Endpoint**: `GET /v2/subindustries/`
* **Deskripsi**: Mengembalikan seluruh pasangan industri dan sub-industri spesifik.
* **Contoh Respon (200 OK)**:
```json
[
  {
    "industry": "banks",
    "sub_industry": "conventional-banks"
  },
  {
    "industry": "banks",
    "sub_industry": "islamic-banks"
  }
]
```

### 1.4 News Tags
* **Endpoint**: `GET /v2/tags/`
* **Deskripsi**: Mengembalikan seluruh tag tematik yang digunakan pada artikel berita dan laporan keterbukaan emiten.
* **Contoh Respon (200 OK)**:
```json
[
  "acquisition",
  "bond-issuance",
  "bullish",
  "dividend",
  "insider-trading",
  "merger",
  "rights-issue"
]
```

---

## 2. Companies Screener (`/v2/companies/`)

Endpoint paling serbaguna untuk menyaring seluruh emiten IDX. Mendukung filter terstruktur (SQL-like) dan bahasa alami (Natural Language).

* **Endpoint**: `GET /v2/companies/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi & Format |
|---|---|---|---|
| `where` | String | Opsional | Kondisi filter ala SQL (misal: `sub_sector = 'Banks' and pe < 12 and market_cap > 5000000000000`). |
| `order_by` | String | Opsional | Field pengurutan. Tambahkan prefix `-` untuk urutan descending (misal: `-market_cap`, `pe`). |
| `desc` | Boolean | Opsional | Apakah urutan dibalik (descending). Default: `false`. |
| `limit` | Integer | Opsional | Maksimal data yang dikembalikan. Default: 10, Maksimal: 200. |
| `offset` | Integer | Opsional | Jumlah item yang dilewati untuk paginasi. |
| `include_query_values` | Boolean | Opsional | Jika `true`, menyertakan nilai metrik yang digunakan dalam query ke respon JSON. |
| `q` | String | Opsional | Query pencarian bahasa alami (contoh: `top 5 mining companies with highest roe`). Jika parameter ini terisi, `where` dan `order_by` diabaikan. |

### Contoh Request SQL-Like:
```bash
curl -X GET "https://api.sectors.app/v2/companies/?where=sub_sector%20%3D%20'metals-mining'%20and%20market_cap%20%3E%2010000000000000&order_by=-roe&limit=5&include_query_values=true" \
     -H "Authorization: $SECTORS_API_KEY"
```

### Contoh Respon JSON:
```json
{
  "results": [
    {
      "symbol": "MDKA.JK",
      "company_name": "Merdeka Copper Gold Tbk.",
      "query_values": {
        "sub_sector": "metals-mining",
        "market_cap": 58200000000000,
        "roe": 0.185
      }
    },
    {
      "symbol": "ANTM.JK",
      "company_name": "Aneka Tambang Tbk.",
      "query_values": {
        "sub_sector": "metals-mining",
        "market_cap": 37100000000000,
        "roe": 0.142
      }
    }
  ],
  "pagination": {
    "total_count": 28,
    "showing": 2,
    "limit": 5,
    "offset": 0,
    "has_next": true,
    "has_previous": false,
    "next_offset": 5,
    "previous_offset": null
  }
}
```

---

## 3. Free Float Market Analysis (`/v2/free-float/`)

Menghitung persentase saham beredar publik (*free float*) dari emiten IDX, diurutkan dari persentase tertinggi ke terendah.

* **Endpoint**: `GET /v2/free-float/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `sector` | String | Opsional | Filter berdasarkan sektor (kebab-case). Contoh: `financials`. |
| `sub_sector` | String | Opsional | Filter berdasarkan subsektor (kebab-case). Contoh: `banks`. |
| `industry` | String | Opsional | Filter berdasarkan industri (kebab-case). |
| `sub_industry` | String | Opsional | Filter berdasarkan sub-industri (kebab-case). |

### Contoh Request:
```bash
curl -X GET "https://api.sectors.app/v2/free-float/?sub_sector=metals-mining" \
     -H "Authorization: $SECTORS_API_KEY"
```

### Contoh Respon JSON:
```json
[
  {
    "symbol": "PADI.JK",
    "company_name": "Minna Padi Investama Sekuritas Tbk",
    "free_float": 0.999
  },
  {
    "symbol": "MEDC.JK",
    "company_name": "Medco Energi Internasional Tbk",
    "free_float": 0.485
  },
  {
    "symbol": "ANTM.JK",
    "company_name": "Aneka Tambang Tbk",
    "free_float": 0.350
  }
]
```
*(Nilai free float dalam desimal, misal 0.350 = 35.0%)*
