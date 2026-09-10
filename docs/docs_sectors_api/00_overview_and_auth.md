# 00. ARSITEKTUR, AUTENTIKASI & KONVENSI API
## Sectors Financial API v2.0.0

Dokumen ini memuat informasi fundamental mengenai arsitektur, metode autentikasi, format parameter, struktur respon, dan konvensi penanganan kesalahan pada Sectors Financial API.

---

## 1. Base URL & Lingkungan

Seluruh pemanggilan endpoint Sectors Financial API versi 2 wajib diarahkan ke basis URL produksi berikut:

```
https://api.sectors.app/v2/
```

* Protokol: `HTTPS` (Wajib, komunikasi non-HTTPS akan ditolak).
* Format Payload & Respon: `application/json`.
* Karakter Encoding: `UTF-8`.

---

## 2. Autentikasi (Authentication)

Sectors Financial API v2 mendukung dua metode autentikasi melalui header HTTP `Authorization`:

### A. Global API Key (Metode Utama untuk Backend / Script / Agent)
API Key diperoleh dari dashboard Sectors akun pengguna (*Settings → API Key Management*). Header dikirimkan langsung dengan nilai API key:

```http
GET /v2/companies/ HTTP/1.1
Host: api.sectors.app
Authorization: YOUR_SECTORS_API_KEY
Content-Type: application/json
```

> **Catatan Penting**: Nilai header dikirim langsung sebagai token string (tanpa prefix `Bearer` untuk API Key standar, atau dengan prefix `Bearer` jika menggunakan OAuth Token).

### B. OAuth2 Bearer Token (Untuk Integrasi Third-Party / ChatGPT / Claude Actions)
```http
Authorization: Bearer <access_token>
```

---

## 3. Format Simbol & Parameter Standar

| Parameter | Format / Tipe | Penjelasan & Contoh |
|---|---|---|
| `{symbol}` | String (4 huruf) | Kode ticker saham bursa Indonesia (IDX). Bersifat *case-insensitive*. Contoh: `BBCA`, `BMRI`, `TLKM`, `ASII`. Suffix `.jk` diperbolehkan namun opsional. |
| `start`, `end` | String `YYYY-MM-DD` | Rentang tanggal kalender. Contoh: `2026-01-01`. Maksimum jendela waktu biasanya 90 hari untuk endpoint transaksi/broker. |
| `sector`, `sub_sector` | String `kebab-case` | Kategori sektor dan subsektor bursa. Contoh: `technology`, `financials`, `banks`, `basic-materials`. Diambil dari endpoint `/v2/subsectors/`. |
| `limit` | Integer | Jumlah maksimum data per halaman (default bervariasi: 10–30, maksimum 200 pada screener). |
| `offset` | Integer | Jumlah data yang dilewati (*skip*) untuk keperluan paginasi. |

---

## 4. Dua Pendekatan Querying: SQL-Like vs Natural Language (NLP)

Pada endpoint pencarian seperti `/v2/companies/`, Sectors API menyediakan dua paradigma pencarian:

### A. SQL-Like Structured Querying (`where`, `order_by`, `desc`)
Memungkinkan filter komparatif dan kondisional yang presisi secara programatik:
* `where`: Ekspresi kondisional field seperti `pe < 15 and roe > 0.15 and market_cap > 1000000000000`.
* `order_by`: Urutan pengurutan field tertentu, misalnya `market_cap` atau `-revenue_growth` (prefix minus untuk descending).
* `desc`: Boolean (`true`/`false`).

### B. Natural Language Querying (`q`)
Menggunakan pemrosesan bahasa alami untuk menerjemahkan pertanyaan pengguna:
* `q`: Parameter teks bebas, misalnya `q=top 10 banking companies with highest dividend yield`.
* *Catatan*: Jika parameter `q` diisi, parameter `where`, `order_by`, `limit`, dan `offset` akan diabaikan oleh engine Sectors.

---

## 5. Kode Status HTTP & Format Error

Sectors API mengembalikan status kode standar HTTP untuk mengindikasikan keberhasilan atau kegagalan request:

| Status Code | Makna | Deskripsi / Penanganan |
|---|---|---|
| `200 OK` | Request Berhasil | Permintaan diproses dan payload data dikembalikan. |
| `400 Bad Request` | Parameter Tidak Valid | Format tanggal salah, parameter wajib tidak diisi, atau format query tidak dikenal. |
| `401 Unauthorized` | Autentikasi Gagal | Header `Authorization` tidak ada atau API Key tidak valid/kadaluarsa. |
| `403 Forbidden` | Akses Dibatasi | Kuota tier akun tidak mencukupi atau fitur memerlukan paket tier lebih tinggi. |
| `404 Not Found` | Data Tidak Ditemukan | Simbol saham tidak terdaftar di IDX atau data laporan keuangan tidak tersedia. |
| `429 Too Many Requests` | Rate Limit Terlampaui | Terlalu banyak request dalam jendela waktu tertentu. Wajib menerapkan *exponential backoff*. |
| `500 Internal Error` | Server Error | Terjadi kesalahan pada upstream server Sectors. |

### Struktur Respon Error Baku:
```json
{
  "detail": "Invalid report_date format. Expected YYYY-MM-DD."
}
```

---

## 6. Contoh Implementasi Klien (Python & cURL)

### Contoh cURL:
```bash
curl -X GET "https://api.sectors.app/v2/financials/quarterly/BBCA/?n_quarters=4" \
     -H "Authorization: $SECTORS_API_KEY" \
     -H "Content-Type: application/json"
```

### Contoh Python (dengan Retry & Timeout):
```python
import os
import time
import requests


class SectorsClient:
    BASE_URL = "https://api.sectors.app/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SECTORS_API_KEY")
        if not self.api_key:
            raise ValueError("SECTORS_API_KEY is required.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "MarketIntelligenceAgent/1.0",
            }
        )

    def get(self, endpoint: str, params: dict | None = None, max_retries: int = 3):
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    wait_sec = 2**attempt
                    time.sleep(wait_sec)
                    continue
                else:
                    response.raise_for_status()
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)
```
