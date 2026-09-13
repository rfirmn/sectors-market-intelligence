# DOKUMENTASI SISTEM, LOGIKA & LANDASAN MATEMATIKA
## Market State Engine — Sectors Market Intelligence Agent (Fase Hari 2)

> **Revisi 13 September 2026 — methodology `2026-09-13-validity-v2`.**
> Ini adalah screener deskriptif, belum model prediksi return. Baca
> [audit desain dan simulasi](engine_design_review_and_simulation.md) untuk penilaian,
> hasil eksperimen yang dapat direproduksi, dan rekomendasi pengembangan.
>
> Perubahan implementasi: QoQ tersedia untuk tampilan, tetapi dikecualikan dari growth
> peer_z. Per keluarga metrik, normalisasi memakai cohort periode persis yang paling
> banyak tersedia (periode terbaru bila seri). Pilihan dicatat di `normalization_periods`,
> pengecualian di `normalization_exclusions`. Ini belum memverifikasi kesegaran data.
> TTM memerlukan empat kuartal berurutan, unik, dan laba lengkap yang finite; angka
> hilang tidak diisi nol. `n<3` atau MAD nol menghasilkan `None`; `n=3..7` ditandai
> `low_sample`. PB dan operating margin tidak memerlukan empat kuartan.
>
> **Verifikasi Empiris Diperbarui (13 September 2026):** Engine telah diuji dengan live
> Sectors API pada **26 perusahaan di 5 subsektor** (automobiles-components, food-beverage,
> oil-gas-coal, telecommunication, properties-real-estate) menggunakan YoY comparison
> (n_quarters=8). Semua 5 subsektor berhasil melakukan peer normalization. Data
> completeness 100%, metric reasonability 99.7% dari 338 checks. Period exclusion
> bekerja: MEDC dikecualikan dari growth peer_z karena period mismatch (Q1 bukan Q2).
> Hasil lengkap: [`live_test_20260913_121803.json`](../data/test_results/live_test_20260913_121803.json).
> Script: [`scripts/live_api_test.py`](../scripts/live_api_test.py).
>
> **Bagian di bawah adalah arsip penjelasan awal, bukan spesifikasi v2.** Diagram dan
> contoh smoke test lama dipertahankan untuk konteks. Klaim yang telah dikoreksi
> dijelaskan di bagian matematika berikut dan laporan audit.

---

## 1. Ringkasan Eksekutif & Paradigma Intelligence

Dokumen ini menyajikan arsitektur sistem, logika finansial, dan pemodelan matematika lengkap dari **Market State Engine** (Modul 2), inti analitis (*intelligence core*) dari Market Intelligence Agent. 

### Paradigma *Variant Perception* (Expectations Investing)
Diadaptasi dari karya Michael Mauboussin (*Expectations Investing*) dan Howard Marks (*Second-Level Thinking*):
> *"Peluang investasi terbaik di pasar modal tidak muncul dari sekadar mengetahui perusahaan mana yang berkinerja baik, melainkan menemukan dislokasi di mana kinerja fundamental perusahaan telah berubah secara signifikan namun ekspektasi harga pasar belum merefleksikannya."*

Pada bursa berkembang seperti **Bursa Efek Indonesia (IDX)**, pendekatan skrining kuantitatif konvensional (misal: mencari emiten dengan PE < 10 atau ROE > 15%) memiliki kelemahan fatal:
1. **Bias Makro & Sektoral**: Pertumbuhan pendapatan +20% pada emiten batu bara di tengah lonjakan harga komoditas global sebenarnya merupakan kinerja medioker jika median subsektornya tumbuh +45%. Sebaliknya, penurunan margin -2% pada emiten ritel di tengah kontraksi daya beli nasional adalah tanda keunggulan kompetitif jika peers terdisrupsi hingga -10%.
2. **Kerapuhan terhadap Outlier Small-Cap**: Ratusan emiten bursa memiliki kapitalisasi mini atau data anomali (misal: laba melonjak 3.000% akibat penjualan aset satu kali). Rata-rata (*mean*) dan deviasi standar (*standard deviation*) klasik akan terdistorsi parah, menghancurkan seluruh normalisasi statistik.
3. **Bias Musiman Kuartalan**: Penjualan kuartal 4 emiten ritel (Desember) selalu melonjak dibanding kuartal 1 (Maret). Perbandingan kuartal-ke-kuartal berurutan (QoQ) menghasilkan sinyal palsu.

**Solusi Market State Engine:**
Membangun mesin komputasi cross-sectional yang menormalisasi kinerja emiten **hanya terhadap peer subsektornya**, menggunakan **statistika kokoh (robust statistics)** yang kebal terhadap outlier ekstrem, dan mengukur disparitas fundamental versus harga secara adil (*peer-normalized z-scores*).

---

## 2. Arsitektur Sistem & Rekayasa Perangkat Lunak

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MARKET STATE ENGINE                               │
│                         (src/engine/ Pipeline)                              │
└─────────────────────────────────────────────────────────────────────────────┘

    [Sectors Financial API v2]
                │
                ▼
   ┌───────────────────────────┐
   │ 1. Taxonomy & Universe    │ ─── Filter Sektor Finansial (Banks, Insurance)
   │    (taxonomy.py)          │ ─── Stripping Suffix .JK (ASII.JK → ASII)
   │                           │ ─── Pagination Handling
   └─────────────┬─────────────┘
                 │
                 ▼
   ┌───────────────────────────┐
   │ 2. Data Ingestion & Cache │ ─── SectorsClient (Snapshot JSON Cache)
   │    (market_state_engine)  │ ─── Offline Fallback Resilient
   └─────────────┬─────────────┘
                 │
                 ▼
   ┌───────────────────────────┐
   │ 3. Metrics Calculator     │ ─── YoY Growth (QoQ Fallback)
   │    (metrics.py)           │ ─── TTM Aggregation (ROE, PE)
   │                           │ ─── Numerical Edge-Case Guards
   └─────────────┬─────────────┘
                 │ MetricSet (Raw Values)
                 ▼
   ┌───────────────────────────┐
   │ 4. Robust Statistics      │ ─── 1%/99% Winsorizing (n ≥ 5)
   │    (stats.py)             │ ─── Sample Median (50% Breakdown Point)
   │                           │ ─── Scaled MAD (k = 1.4826 consistency factor)
   │                           │ ─── Peer-Normalized z = (x - med) / (1.4826*MAD)
   └─────────────┬─────────────┘
                 │ PeerZScores + SubsectorProfile
                 ▼
   ┌───────────────────────────┐
   │ 5. Pipeline Orchestrator  │ ─── Deterministic Assembly
   │    (CompanyState Output)  │ ─── Full Provenance Metadata
   └───────────────────────────┘
```

### A. Pembagian Modul & Batasan Tanggung Jawab

| Modul | Lokasi File | Tanggung Jawab Utama |
|---|---|---|
| **Data Contracts** | [`src/engine/models.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/models.py) | Definisi struktur data immutabel/dataclass: `MetricSet`, `PeerZScores`, `CompanyState`, `MetricDistribution`, `SubsectorProfile`, `CompanyInfo`, `MarketStateResult`. |
| **Robust Statistics** | [`src/engine/stats.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/stats.py) | Algoritma matematika pure-Python: Linear percentile, Winsorizing, Median, MAD, dan konsistensi penskalaan normalitas. |
| **Taxonomy & Universe** | [`src/engine/taxonomy.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/taxonomy.py) | Pengambilan taksonomi, eksklusi sektor finansial, pembersihan ticker `.JK`, perakitan universe non-finansial per subsektor. |
| **Metrics Calculator** | [`src/engine/metrics.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/metrics.py) | Perhitungan 8 metrik finansial mentah, pemilihan YoY vs QoQ, agregasi TTM, penanganan limit matematika (denominator nol, ekuitas negatif). |
| **Pipeline Orchestrator** | [`src/engine/market_state_engine.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/market_state_engine.py) | Koordinasi end-to-end: universe builder $\to$ data ingestion $\to$ kalkulasi metrik $\to$ normalisasi subsektor $\to$ perakitan output deterministik. |

### B. Prinsip *Zero Heavy External Dependencies*
Seluruh komputasi matematika di [`src/engine/stats.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/stats.py) dibangun **100% menggunakan Python Standard Library** (`math`, `statistics`, `collections.abc`). 
- **Keuntungan**: Tidak memerlukan NumPy, SciPy, atau pustaka kompilasi C berat lainnya.
- **Dampak**: Waktu booting sub-detik, isolasi dependensi sempurna, kompatibilitas deployment multi-platform (macOS/Linux/Docker), dan kontrol penuh atas perlakuan terhadap edge case numerik (*no silent NaN poisoning*).

---

## 3. Logika Finansial & Domain Intelligence

### A. Aturan Eksklusi Sektor Finansial (§6.1 `project.md`)
```python
EXCLUDED_SECTOR = "financials"
# Subsektor tereliminasi: banks, financing-service, insurance,
# investment-service, holding-investment-companies
```
**Rasionalitas Keuangan:**
1. **Struktur Neraca yang Fundamental Berbeda**: Bagi bank dan multifinance, kas dan pinjaman adalah persediaan (*inventory*), sedangkan deposito/utang adalah instrumen operasional utama. Rasio solvabilitas umum seperti *Debt-to-Equity* atau perputaran modal kerja tidak memiliki arti ekonomi yang sama seperti pada industri manufaktur.
2. **Distorsi Operating Margin**: Bank tidak memiliki metrik *Operating Profit* konvensional (menggunakan *Net Interest Income*). Memasukkan bank ke dalam pooling komputasi margin akan merusak estimasi median dan MAD subsektor secara sistemik.

### B. Strategi Pertumbuhan: YoY-First dengan Fallback QoQ
```
            Tahun t-1                         Tahun t
        ┌──────────────┐                 ┌──────────────┐
        │ Q2 (t-1)     │ ─── YoY Growth ─▶│ Q2 (t)       │  (Ideal: Menghilangkan musiman)
        └──────────────┘                 └──────────────┘
                                                ▲
                                                │ QoQ Fallback
                                         ┌──────┴───────┐
                                         │ Q1 (t)       │  (Jika data t-1 belum tersedia)
                                         └──────────────┘
```
1. **Prioritas Utama (YoY)**:
   - Membandingkan kuartal yang sama pada tahun berjalan terhadap tahun sebelumnya (misal: Q2 2026 vs Q2 2025).
   - Mengurangi musiman kuartalan, tetapi tidak menghilangkan pergeseran Ramadhan/Lebaran, kalender fiskal, dan perubahan bauran usaha.
2. **Fallback Mulus (QoQ)**:
   - Jika emiten baru melantai di bursa (IPO) atau data historis di bawah 5 kuartal, sistem secara otomatis beralih membandingkan kuartal berjalan terhadap kuartal sebelumnya (misal: Q2 2026 vs Q1 2026).
   - Metode dicatat pada `growth_method`. Sejak v2, QoQ hanya untuk tampilan dan tidak digabungkan dengan YoY dalam growth peer_z. Pasangan YoY dicari berdasarkan periode yang cocok, meskipun hanya dua observasi tersedia.

### C. Trailing Twelve Months (TTM) untuk Metrik Level
Metrik yang mengukur efisiensi modal dan valuasi relatif wajib dihitung menggunakan TTM akumulatif, bukan kuartal tunggal yang di-annualisasi:
- **Return on Equity (ROE TTM)**:
  $$\text{ROE}_{\text{TTM}} = \frac{\sum_{k=0}^{3} \text{Earnings}_{Q-k}}{\text{Total Equity}_{\text{latest}}}$$
  *Alasan*: Mencegah volatilitas kuartal tunggal (misal kuartal dengan pembayaran dividen anak usaha atau keuntungan kurs valas) mendistorsi persepsi profitabilitas modal jangka panjang.
- **Price-to-Earnings (PE TTM)**:
  $$\text{PE}_{\text{TTM}} = \frac{\text{Market Cap}}{\sum_{k=0}^{3} \text{Earnings}_{Q-k}}$$
  *Alasan*: Melindungi dari anomali "PE palsu murah/mahal" akibat kinerja kuartal musiman.

### D. Taksonomi Penanganan Edge Cases Numerik

| Kondisi Data | Pemeriksaan Guard | Tindakan Sistem |
|---|---|---|
| **Denominator Penjualan Nol** | `abs(rev_prev) < 1_000_000` | `revenue_growth = None` (tidak membagi dengan nol) |
| **Pembalikan Rugi ke Laba (Loss-to-Profit)** | `earnings_prev < 0` dan `earnings_curr > 0` | Menggunakan `abs(earnings_prev)` sebagai penyebut: pertambahan nilai tetap positif dan terukur. |
| **Ekuitas Negatif** | `total_equity <= 0` | `roe_ttm = None`, `pb = None` (emiten insolven secara teknis) |
| **Laba TTM Negatif / Nol** | `ttm_earnings <= 0` | `pe_ttm = None` (PE bernilai negatif tidak memiliki makna rasio) |
| **Data Harga Kurang dari 2 Titik** | `len(daily) < 2` atau `close_earliest <= 0` | `price_return = None` |
| **Data Historis Kuartal < 2** | `len(valid_quarters) < 2` | Semua metrik pertumbuhan diatur ke `None` |
| **Subsektor Kecil ($n < 3$)** | `n_valid < 3` | `peer_z = None`; ketidaktersediaan informasi bukan nilai median |

---

## 4. Landasan Matematika Lengkap (Mathematical Foundations)

Normalisasi dilakukan secara terpisah untuk setiap subsektor dan setiap metrik finansial.

### A. Linear Interpolation Percentile
Untuk urutan nilai yang telah diurutkan $\mathbf{x} = [x_0, x_1, \dots, x_{n-1}]$ secara menaik:
Indeks kontinu dari persentil $p \in [0, 1]$ dihitung dengan:
$$i = p \cdot (n - 1)$$
Didekomposisi menjadi bagian integer $i_{\text{lo}} = \lfloor i \rfloor$, $i_{\text{hi}} = \min(i_{\text{lo}} + 1, n - 1)$, dan fraksi $\Delta = i - i_{\text{lo}}$.
Nilai persentil terinterpolasi:
$$\hat{Q}(p) = x_{i_{\text{lo}}} \cdot (1 - \Delta) + x_{i_{\text{hi}}} \cdot \Delta$$

### B. Two-Sided Symmetric Winsorizing (1% & 99%)
Sebelum menghitung parameter dispersi, outlier ekstrem dijinakkan menggunakan Winsorizing:
$$x_i^* = \begin{cases} 
\hat{Q}(0.01) & \text{jika } x_i < \hat{Q}(0.01) \\ 
\hat{Q}(0.99) & \text{jika } x_i > \hat{Q}(0.99) \\ 
x_i & \text{lainnya}
\end{cases}$$
- **Guard Ukuran Sampel ($n < 5$)**: Jika jumlah emiten dalam subsektor $n < 5$, winsorizing ditiadakan ($x_i^* = x_i$) karena pemotongan persentil pada sampel mikro tidak memiliki kekuatan statistik.

### C. Estimator Lokasi: Sample Median ($\tilde{x}$)
Median dipilih karena breakdown point asimptotik mendekati 50%. Ini adalah batas ketahanan terhadap kontaminasi arbitrer, bukan jaminan akurasi ketika hampir setengah sampel rusak. Bias dapat muncul jauh sebelum batas itu tercapai.

### D. Estimator Skala: Median Absolute Deviation (MAD)
MAD mengukur dispersi nilai terhadap median:
$$\text{MAD}(\mathbf{x}^*) = \text{median}\left(\left| x_i^* - \tilde{x} \right|\right)$$

---

### E. Penurunan Matematika Consistency Factor ($k = 1.4826$)

#### 1. Masalah pada Raw MAD
Pada spesifikasi awal beberapa pustaka umum, formula skor-z MAD sering ditulis secara naif:
$$\text{raw\_z}(x_i) = \frac{x_i - \tilde{x}}{\text{MAD}}$$
Untuk distribusi normal, MAD populasi adalah sekitar $0.67449\sigma$. Hubungan konstanta berikut khusus asumsi normal, bukan semua distribusi simetris.

#### 2. Penurunan Analitis
Misalkan variabel acak terdistribusi normal standar $Z \sim \mathcal{N}(0, 1)$ dengan fungsi distribusi kumulatif $\Phi(z)$.
Berdasarkan definisi, MAD adalah median dari $|Z|$:
$$P(|Z| \le \text{MAD}) = 0.50$$
Karena distribusi normal bersifat simetris terhadap 0:
$$P(-\text{MAD} \le Z \le \text{MAD}) = 2\Phi(\text{MAD}) - 1 = 0.50$$
$$2\Phi(\text{MAD}) = 1.50 \implies \Phi(\text{MAD}) = 0.75$$
$$\text{MAD} = \Phi^{-1}(0.75) \approx 0.67448975$$

Untuk distribusi normal umum $X \sim \mathcal{N}(\mu, \sigma^2)$:
$$\text{MAD}(X) = \Phi^{-1}(0.75) \cdot \sigma \approx 0.6745 \cdot \sigma$$

Agar MAD menjadi estimator skala yang **konsisten secara asimptotik di bawah normalitas**, kalikan dengan $k$. Konsisten tidak berarti tak-bias pada sampel kecil:
$$k = \frac{1}{\Phi^{-1}(0.75)} = \frac{1}{0.67448975} \approx 1.4826022 \dots \approx \mathbf{1.4826}$$
Maka estimator standar deviasi yang kokoh didefinisikan sebagai:
$$\hat{\sigma}_{\text{robust}} = 1.4826 \times \text{MAD}$$

#### 3. Bukti Dampak Empiris pada Seleksi Peluang
Jika sistem menggunakan raw MAD tanpa faktor $1.4826$, maka skor-z akan mengalami **inflasi buatan sebesar 48.26%**:
$$\text{raw\_z} = 1.4826 \times \text{scaled\_z}$$

**Angka arsip yang belum dapat diverifikasi:** draf sebelumnya menyebut simulasi 700 emiten/28 subsektor dengan angka berikut. Skrip, seed, dataset, dan hasil mentah pendukungnya tidak ditemukan pada audit; tabel ini tidak boleh dipakai sebagai bukti empiris IDX.

| Ambang Batas Discrepancy | Persentase Lolos (Raw MAD Tanpa $k$) | Persentase Lolos (Scaled MAD dengan $k=1.4826$) |
|---|:---:|:---:|
| **Threshold > 1.0 (Kandidat)** | **26.1% (183 emiten)** $\longrightarrow$ Terlalu banyak noise! | **18.9% (132 emiten)** $\longrightarrow$ Selektif & proporsional |
| **Threshold > 1.5 (HIGH Priority)** | **15.1% (106 emiten)** $\longrightarrow$ 100+ emiten HIGH priority | **8.6% (60 emiten)** $\longrightarrow$ Target investigasi presisi |

**Koreksi:** faktor tersebut mengubah unit skala, tetapi tidak menjadikan skor tepat normal ataupun mengalibrasi probabilitas ambang discrepancy. Bukti simulasi yang dapat direproduksi kini berada di [hasil simulasi](research/simulation_results.md).

---

### F. Formula Akhir Peer Z-Score & Penanganan Singularitas
Formula normalisasi akhir per emiten $i$ dalam subsektor $S$:
$$\text{peer\_z}(x_i) = \frac{x_i - \tilde{x}}{\text{scale}}$$

Di mana $\text{scale}$ ditentukan melalui logika berjenjang (*anti-division-by-zero*):
$$\text{scale} = \begin{cases}
1.4826 \times \text{MAD} & \text{jika } \text{MAD} > 0 \\
0.0 & \text{jika } \text{MAD} = 0
\end{cases}$$

**Aturan Penentuan Skor Akhir:**
1. Jika ukuran sampel valid $n_{\text{sample}} < 3$: $\text{peer\_z} = \text{None}$.
2. Jika $\text{scale} = 0.0$: $\text{peer\_z} = \text{None}$. MAD nol juga dapat terjadi ketika mayoritas nilai sama walaupun beberapa nilai berbeda. Fallback 1% median dihapus karena tidak invarian terhadap translasi.
3. Jika metrik mentah $x_i = \text{None}$: $\text{peer\_z} = \text{None}$.

### G. Invarian Matematika yang Terbukti Secara Formal
Implementasi diperiksa pada kasus unit test; ini bukan pembuktian formal atau validasi investasi. Untuk skala positif dan sampel cukup:
* **Identitas Titik Pusat**: $\text{peer\_z}(\tilde{x}) = 0.0000$ (emiten di median selalu bernilai 0).
* **Konservasi Tanda Monotonik**: $\text{sgn}(\text{peer\_z}(x_i)) = \text{sgn}(x_i - \tilde{x})$.
* **Batas ketahanan**: median/MAD lebih tahan terhadap outlier, tetapi besarnya pergeseran bergantung pada sampel. Numerator memakai nilai mentah, sehingga skor individual tidak dibatasi winsorizing. Klaim batas universal dari unit test draf awal ditarik.

---

## 5. Bukti Verifikasi Empiris — Live API Test (26 Companies, 5 Subsectors)

Engine diverifikasi menggunakan **live Sectors API** pada 13 September 2026 dengan script
[`scripts/live_api_test.py`](../scripts/live_api_test.py) dan data YoY (`n_quarters=8`).
Hasil lengkap tersimpan di [`data/test_results/live_test_20260913_121803.json`](../data/test_results/live_test_20260913_121803.json).

### Universe yang Diuji

| Subsektor | Companies (n) | Growth Method | Status |
|---|:---:|---|---|
| automobiles-components | 5 | YoY Q2-2026 vs Q2-2025 | ✅ Normalization working |
| food-beverage | 6 | YoY Q2-2026 vs Q2-2025 | ✅ Normalization working |
| oil-gas-coal | 5 | YoY Q2-2026 vs Q2-2025 | ✅ Normalization working |
| telecommunication | 5 | YoY Q2-2026 vs Q2-2025 | ✅ Normalization working |
| properties-real-estate | 5 | YoY Q2-2026 vs Q2-2025 | ✅ Normalization working |

### Hasil Ringkasan

```
┌─────────────────────────────────────────────────────────┐
│  PROFESSIONAL SCENARIO — Score: 99.9/100                │
│  26 companies, 5 subsectors, live API + cache           │
├─────────────────────────────────────────────────────────┤
│  Data Completeness    : 100.0% (26/26 companies)        │
│  Metric Reasonability : 99.7% (337/338 checks)          │
│  Normalization Working: 5/5 subsectors                  │
│  Good Subsectors      : 5/5                             │
│  Duration             : 16.7 seconds                   │
└─────────────────────────────────────────────────────────┘
```

### Contoh Output Per Subsektor: automobiles-components

```
Distribution Statistics (n=5, low_sample):
  revenue_growth  : median=0.0893, MAD=0.0911, scaled_MAD=0.1351
  earnings_growth : median=-0.0385, MAD=0.1828, scaled_MAD=0.2710
  margin_change   : median=-0.0100, MAD=0.0091, scaled_MAD=0.0134
  roe_ttm         : median=0.1384, MAD=0.0356, scaled_MAD=0.0528
  price_return    : median=0.0327, MAD=0.0174, scaled_MAD=0.0258

Peer Z-Scores:
  Sym    zRevGr   zEarnGr  zMargΔ   zROE     zPriceR
  ASII   -0.684   -0.674   -0.955   -0.674   —
  AUTO   +0.771   +1.497   +0.674   +0.042   +4.074
  BOLT   -0.436   +0.000   +2.143   +0.000   -0.535
  IMAS   +1.019   -2.621   +0.000   -2.509   +0.535
  SMSM   +0.000   +0.654   -0.014   +2.170   -0.814

Catatan: ASII dikecualikan dari z_price_return karena period mismatch
         (data cache dari periode berbeda dengan cohort peer).
```

### Perilaku Guard yang Terverifikasi

| Guard | Contoh Kasus | Hasil |
|---|---|---|
| **Period mismatch exclusion** | MEDC (Q1-2026, bukan Q2) dikecualikan dari growth peer_z | `normalization_exclusions: {revenue_growth: period_mismatch_or_missing, ...}` |
| **Price period mismatch** | ASII price dari cache lama dikecualikan | `normalization_exclusions: {price_return: period_mismatch_or_missing}` |
| **n<3 → None** | Single-company lookup (beginner scenario) | Semua z-scores = None |
| **MAD=0 → None** | Tidak terjadi pada live test; diverifikasi oleh unit test | `peer_z = None` |
| **Numerator unbounded** | LPKR earnings_growth=+1115% → z_earnings=+40.0 | Output valid — engine tidak membatasi sinyal ekstrem |

### Catatan Desain: Numerator Tidak Dibatasi

Seperti dijelaskan di §4.G, numerator `(x_i - median)` tidak dibatasi oleh winsorizing.
Winsorizing hanya diterapkan pada **sampel peer** untuk menghitung median dan MAD yang robust.
Nilai individual `x_i` sendiri tidak di-clip.

Ini **disengaja**: engine sebagai intelligence tool harus mampu membedakan setiap company,
termasuk yang memiliki perubahan ekstrem. Membatasi z-score individual akan menghilangkan
differensiasi yang justru menjadi nilai utama sistem.

---

## 6. Status Kepatuhan Terhadap Spesifikasi Kompetisi (`project.md`)

| Kebutuhan Teknis | Ref `project.md` | Status Implementasi |
|---|:---:|:---:|
| **Eksklusi Perbankan & Asuransi** | §6.1 | ✅ Selesai di [`src/engine/taxonomy.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/taxonomy.py) |
| **Pembersihan Suffix `.JK`** | §6.1 | ✅ Selesai (`strip_jk_suffix`) |
| **8 Metrik Finansial Inti** | §6.1 | ✅ Selesai di [`src/engine/metrics.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/metrics.py) |
| **Winsorizing 1% & 99%** | §6.1 | ✅ Selesai di [`src/engine/stats.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/stats.py) |
| **Median & Scaled MAD ($k=1.4826$)** | §6.1 | ✅ Selesai di [`src/engine/stats.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/stats.py) |
| **Struktur Data `CompanyState`** | §6.1 | ✅ Selesai di [`src/engine/models.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/engine/models.py) |
| **Provenance Tracking Lengkap** | §6.1 | ✅ Selesai (`growth_period`, `growth_method`, `price_period`) |
| **Fail-Safe Offline Cache** | §6.10 | ✅ Selesai di [`src/client/cache.py`](file:///Users/rio/Documents/RIO/Pemrograman/my_product/market-intelligence/src/client/cache.py) |
| **Test Coverage & Zero Warnings** | §10 | ✅ 104/104 tests pass, 0 ruff errors, 0 pyright errors |
