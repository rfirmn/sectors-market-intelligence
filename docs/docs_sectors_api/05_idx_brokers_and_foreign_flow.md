# 05. BROKER SUMMARY & FOREIGN FLOW IDX
## Sectors Financial API v2.0.0

Modul ini mendokumentasikan data mikrostruktur pasar IDX yang menjadi keunggulan unik (*moat*) Sectors API: arus dana investor asing (*Daily Net Foreign Inflow*), direktori anggota bursa (*Broker Registry*), peringkat broker harian, serta rincian akumulasi dan distribusi bandar/institusi (*Broker Summary*).

Endpoint ini menggerakkan **Confirmation Layer (§6.5 `project.md`)** pada pipeline Market Intelligence Agent.

---

## 1. Daily Net Foreign Inflow (`/v2/foreign-flow/{symbol}/`)

Mengembalikan aliran dana bersih broker asing (dalam Rupiah) per hari untuk satu simbol IDX dalam rentang hingga 90 hari.

* **Endpoint**: `GET /v2/foreign-flow/{symbol}/`
* **Metode**: `GET`
* **Header**: `Authorization: YOUR_SECTORS_API_KEY`

### Parameter Path & Query:
| Parameter | Tipe | Lokasi | Wajib? | Deskripsi |
|---|---|---|---|---|
| `symbol` | String | Path | **Ya** | Kode emiten IDX (misal: `BBCA`, `ASII`, `GOTO`). |
| `start` | String | Query | Opsional | Tanggal mulai `YYYY-MM-DD`. Default: 30 hari sebelum `end`. |
| `end` | String | Query | Opsional | Tanggal akhir `YYYY-MM-DD`. Default: Hari ini. |

### Interpretasi Angka:
* Nilai `net_foreign_inflow > 0`: Broker asing melakukan **Net Buy** (akumulasi modal masuk).
* Nilai `net_foreign_inflow < 0`: Broker asing melakukan **Net Sell** (distribusi modal keluar).

### Contoh Respon JSON:
```json
{
  "symbol": "BBCA.JK",
  "start": "2025-05-01",
  "end": "2025-05-05",
  "data": [
    {
      "date": "2025-05-02",
      "net_foreign_inflow": 128450000000
    },
    {
      "date": "2025-05-05",
      "net_foreign_inflow": -45200000000
    }
  ]
}
```

---

## 2. Direktori Anggota Bursa / Broker Registry (`/v2/brokers/`)

Mengembalikan daftar lengkap sekuritas anggota bursa IDX terkurasi beserta profil klasifikasinya (asal dan kohort).

* **Endpoint**: `GET /v2/brokers/`
* **Metode**: `GET`

### Parameter Query:
| Parameter | Tipe | Wajib? | Deskripsi |
|---|---|---|---|
| `origin` | String | Opsional | `foreign` (sekuritas asing) atau `domestic` (sekuritas lokal). |
| `cohort` | String | Opsional | Klasifikasi tipe nasabah utama: `retail`, `institutional`, `mixed`, `unknown`. |

### Contoh Respon JSON:
```json
[
  {
    "code": "AK",
    "name": "UBS Sekuritas Indonesia",
    "is_foreign": true,
    "cohort": "institutional",
    "license_type": "PPE, PEE"
  },
  {
    "code": "YP",
    "name": "Mirae Asset Sekuritas Indonesia",
    "is_foreign": false,
    "cohort": "retail",
    "license_type": "PPE, PEE"
  },
  {
    "code": "CC",
    "name": "Mandiri Sekuritas",
    "is_foreign": false,
    "cohort": "mixed",
    "license_type": "PPE, PEE, MI"
  }
]
```

---

## 3. Peringkat Broker Harian (`/v2/brokers/top/`)

Peringkat sekuritas teraktif pada tanggal tertentu berdasarkan nilai total perdagangan kotor (*gross trade value*) atau aliran dana bersih (*net flow*).

* **Endpoint**: `GET /v2/brokers/top/`
* **Parameter Query**:
  * `date`: Tanggal target `YYYY-MM-DD`.
  * `metric`: `gross` (akumulasi beli + jual) atau `net` (nilai beli dikurangi jual).
  * `origin`: `all`, `foreign`, atau `domestic`.
  * `cohort`: `all`, `retail`, `institutional`, `mixed`.
  * `n_brokers`: Jumlah broker yang ditampilkan (default: semua yang cocok).

---

## 4. Broker Summary per Emiten

Mengurai sekuritas mana saja yang melakukan transaksi pada suatu saham tertentu:

### 4.1 Rincian Broker per Simbol (`/v2/broker-summary/{symbol}/`)
* **Endpoint**: `GET /v2/broker-summary/{symbol}/`
* **Deskripsi**: Data harian tiap broker yang memperdagangkan saham tersebut dalam jendela waktu hingga 14 hari (nilai beli, jual, net, lot, dan rata-rata harga pelaksanaan/VWAP).
* **Parameter**: `symbol` (Path), `broker_code` (Query opsional, misal: `AK`), `start`, `end`.

### 4.2 Top Pembeli & Penjual Saham (`/v2/broker-summary/{symbol}/top/`)
* **Endpoint**: `GET /v2/broker-summary/{symbol}/top/`
* **Deskripsi**: Daftar sekuritas *top buyers* (net buy terbesar) dan *top sellers* (net sell terbesar) pada saham tersebut dalam rentang hingga 30 hari. Sangat efektif mendeteksi akumulasi bandar/institusi.
* **Parameter**: `symbol` (Path), `origin`, `cohort`, `n_brokers` (default 5).

### Contoh Respon JSON Top Buyers & Sellers:
```json
{
  "symbol": "BBCA.JK",
  "start": "2025-05-01",
  "end": "2025-05-14",
  "origin": "all",
  "cohort": "all",
  "top_buyers": [
    {
      "broker_code": "AK",
      "broker_name": "UBS Sekuritas Indonesia",
      "net_buy_value": 450200000000,
      "avg_price": 8950
    }
  ],
  "top_sellers": [
    {
      "broker_code": "YP",
      "broker_name": "Mirae Asset Sekuritas Indonesia",
      "net_sell_value": -320100000000,
      "avg_price": 8925
    }
  ]
}
```

---

## 5. Aktivitas Perdagangan per Broker

Melihat portofolio transaksi satu broker terhadap berbagai saham di bursa:

### 5.1 Aktivitas Broker Berdasarkan Kode (`/v2/broker-activity/{broker_code}/`)
* **Endpoint**: `GET /v2/broker-activity/{broker_code}/`
* **Deskripsi**: Daftar seluruh saham yang dibeli/dijual oleh satu broker dalam rentang 14 hari.

### 5.2 Top Akumulasi & Distribusi Broker (`/v2/broker-activity/{broker_code}/top/`)
* **Endpoint**: `GET /v2/broker-activity/{broker_code}/top/`
* **Deskripsi**: Peringkat saham yang paling gencar diakumulasi (*top accumulations*) atau dilepas (*top distributions*) oleh sekuritas tersebut.
