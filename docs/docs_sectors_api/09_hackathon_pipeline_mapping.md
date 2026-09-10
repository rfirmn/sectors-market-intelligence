# 09. PEMETAAN PIPELINE MARKET INTELLIGENCE AGENT KE SECTORS API
## Sectors Hackathon 2026 — Track: Market Intelligence

Dokumen ini menjadi jembatan operasional antara spesifikasi produk [project.md](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/project.md) dan panggilan riil endpoint Sectors Financial API v2. Memastikan pemenuhan syarat penilaian hackathon: *derived insight*, pemanfaatan multi-endpoint Sectors, komputasi riil non-mock, dan integritas loop `NUMERICAL → LINGUISTIC → NUMERICAL`.

---

## 1. Matriks Alokasi Endpoint Sectors per Tahap Pipeline

Sistem Market Intelligence Agent memanfaatkan **6 kategori endpoint Sectors yang berbeda dan saling melengkapi** sepanjang siklus analisis:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ALUR INTEGRASI ENDPOINT SECTORS PER TAHAP                       │
└────────────────────────────────────────────────────────────────────────────────────────┘

 [1. Universe & Exclusion] ──► GET /v2/subsectors/ + GET /v2/companies/
                               (Eliminasi sektor finansial/perbankan)
                                        │
                                        ▼
 [2. Market State Engine]  ──► GET /v2/financials/quarterly/{symbol}/ (Kuartalan)
                               GET /v2/daily/{symbol}/ (Harga & Return)
                               (Hitung 8 metrik + Winsorized subsector Median/MAD)
                                        │
                                        ▼
 [3. Discovery Engine]     ──► (Derivasi matematika murni dari CompanyState:
                                discrepancy = fundamental_z - price_z; >1.0 & >1.5)
                                        │
                                        ▼
 [4. Smart Research]       ──► 1. GET /v2/filings/?symbol={symbol} (Insider trading)
                               2. GET /v2/company/corporate-actions/{symbol}/
                               3. GET /v2/news/?symbols={symbol}
                               (Mosaic kualitatif 1-pass LLM: FOR vs AGAINST)
                                        │
                                        ▼
 [5. Confirmation Layer]   ──► GET /v2/foreign-flow/{symbol}/
                               (Cek arah akumulasi/distribusi net broker asing)
                                        │
                                        ▼
 [6. Numerical Challenge]  ──► (Kalkulasi independen 3 skenario z-score:
                                Base, Conservative = z-1, Stress = 0)
                                        │
                                        ▼
 [7. Opportunity Memo]     ──► Sintesis terstruktur + Inline Provenance + Disclaimer
```

---

## 2. Rincian Teknis Integrasi per Modul

### Tahap 1: Eksklusi Sektor Finansial & Pembentukan Universe
* **Tujuan**: Membentuk daftar emiten non-finansial yang sebanding.
* **Endpoint**:
  * `GET /v2/subsectors/`: Mengambil taksonomi sektor dan subsektor.
  * `GET /v2/companies/?limit=200`: Mengambil daftar emiten.
* **Rule Filter (§6.1)**:
  ```python
  EXCLUDED_SECTORS = ["financials"]
  # Sektor perbankan, asuransi, dan multifinance dieliminasi
  # karena struktur laporan keuangan berbeda (NII, Gross Loan, bukan Gross Margin).
  ```

---

### Tahap 2: Market State Engine (Kalkulasi 8 Metrik & `peer_z`)
* **Endpoint**:
  * `GET /v2/financials/quarterly/{symbol}/?n_quarters=4`: Menarik 4 kuartal terakhir emiten untuk menghitung:
    1. Revenue growth (YoY / QoQ)
    2. Earnings growth (YoY / QoQ)
    3. Margin (Operating PnL / Revenue) & perubahannya
    4. ROE (Earnings / Total Equity)
    5. Valuasi relatif (PE / PB)
  * `GET /v2/daily/{symbol}/?start={start}&end={end}`: Menghitung:
    6. Price return (periode berjalan)
* **Normalisasi Statistik**:
  * Lakukan winsorizing persentil 1% dan 99% per subsektor.
  * Hitung `median` dan `MAD` (Median Absolute Deviation) per subsektor.
  * Hitung skor standar emiten:
    $$peer\_z(metric) = \frac{company\_metric - median(peer\_metric)}{MAD(peer\_metric)}$$

---

### Tahap 3: Opportunity Discovery Engine (Variant Perception Detector)
* **Karakteristik**: Komputasi numerik internal, tidak memerlukan endpoint baru.
* **Formula Kunci**:
  * $fundamental\_z = \text{average}(z(\text{revenue\_growth}), z(\text{earnings\_growth}), z(\text{margin\_change}))$
  * $price\_z = z(\text{price\_return})$
  * $discrepancy = fundamental\_z - price\_z$
* **Threshold Terkunci A Priori**:
  * $discrepancy > 1.0 \rightarrow$ Opportunity Candidate
  * $discrepancy > 1.5 \rightarrow$ HIGH Priority

---

### Tahap 4: Smart Research (Mosaic Evidence Gathering)
* **Tujuan**: Menjawab apakah dislokasi terjadi karena pasar lambat menyadari (*mispricing*) atau karena pasar punya alasan skeptis yang sah.
* **Urutan Penarikan Data Kualitatif Sectors (Hierarki Mosaic)**:
  1. `GET /v2/filings/?symbol={symbol}&limit=10`: Deteksi apakah ada pembelian/penjualan oleh direksi atau pemegang saham pengendali (*insider buying*).
  2. `GET /v2/company/corporate-actions/{symbol}/`: Cek pembagian dividen terbaru atau aksi korporasi lainnya.
  3. `GET /v2/news/?symbols={symbol}&limit=10`: Telusuri katalis berita bursa terkait efisiensi biaya, peluncuran produk baru, atau risiko makro.
  4. *Fallback Web Search*: Hanya dipicu jika ketiga endpoint di atas menghasilkan kurang dari 2 bukti faktual.
* **Format Output Prompt LLM**: Tepat 2–4 bullet terbagi dalam `Evidence FOR` (mendukung tesis perbaikan) dan `Evidence AGAINST` (faktor risiko/skeptisisme pasar), lengkap dengan sitasi sumber.

---

### Tahap 5: Confirmation Layer (Mikrostruktur Asing)
* **Tujuan**: Menilai apakah pelaku pasar institusi asing searah dengan tesis dislokasi fundamental.
* **Endpoint**: `GET /v2/foreign-flow/{symbol}/?start={last_30_days}&end={today}`
* **Logika Evaluasi**:
  * Ambil total akumulatif `net_foreign_inflow` periode observasi.
  * Jika $discrepancy > 0$ dan $\sum net\_foreign\_inflow > 0 \rightarrow$ **`SUPPORTIVE`**
  * Jika arah berlawanan $\rightarrow$ **`MIXED / CONTRARY`** (Wajib dimasukkan sebagai poin utama dalam *Counter-Thesis*).

---

### Tahap 6: Numerical Challenge Engine (Stress Testing)
* **Tujuan**: Menguji apakah tesis bertahan saat keunggulan fundamental mengalami regresi ke rata-rata sektornya.
* **Kalkulasi Deterministik**:
  * **BASE**: $fundamental\_z$ aktual $\rightarrow$ Status: `Thesis survives`
  * **CONSERVATIVE**: $fundamental\_z - 1.0$ (mundur 1 standar deviasi peer) $\rightarrow$ Status: `Thesis survives`
  * **STRESS**: $fundamental\_z = 0$ (reversi penuh ke median peer) $\rightarrow$ Status: `Thesis weakens`
* **Prinsip Anti-Halusinasi**: LLM **tidak pernah** menghitung angka skenario. Engine numerik Python menghitung angka batas toleransi dan survival status, lalu menyerahkannya ke generator memo.

---

### Tahap 7: Opportunity Memo Synthesizer & Provenance
* **Output Akhir**: Merangkum hasil komputasi dan sintesis ke dalam format memo baku [project.md §6.8](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/project.md#L298).
* **Provenance Inline**: Setiap angka menyertakan catatan sumber (misal: *"vs subsector metals-mining via Sectors API Q2 2026"*).
* **Disclaimer Kepatuhan Wajib**:
  > *"This is a research-prioritization tool, not financial advice. It does not predict returns or guarantee outcomes."*

---

## 3. Strategi Keandalan Demo (Demo Reliability Mechanism §6.10)

Untuk menjamin kelancaran demo video dan evaluasi juri tanpa memalsukan data (*no faking*):
1. **Live Computation**: Kode di repo memanggil Sectors API secara riil dan menjalankan algoritma normalisasi matematika asli.
2. **Deterministic Pre-flight Snapshot Cache**:
   Setiap response sukses dari Sectors API disimpan ke direktori lokal cache (`.cache/sectors/` atau SQLite).
   Jika saat rekaman/penilaian live koneksi internet mengalami latensi atau Sectors API terkena limit 429, sistem otomatis membaca snapshot cache terakhir dengan notifikasi log transparan, memastikan demo berjalan mulus tanpa berpura-pura (*fail-safe live execution*).
