# 08. SPESIALISASI SEKTOR PERTAMBANGAN RI (ESDM & MINERBA)
## Sectors Financial API v2.0.0

Indonesia merupakan salah satu produsen komoditas tambang terbesar dunia (nikel, batu bara, tembaga, timah, emas). Sectors Financial API menyediakan **19 endpoint spesialis** yang mengagregasi data resmi Kementerian ESDM, Ditjen Minerba, serta laporan operasional emiten tambang.

---

## 1. Perusahaan Tambang (Mining Companies)

### 1.1 Daftar Perusahaan Tambang (`/v2/mining/companies/`)
* **Endpoint**: `GET /v2/mining/companies/`
* **Deskripsi**: Mencari perusahaan tambang berdasarkan nama, kode saham, slug, atau komoditas.
* **Parameter Query**: `commodity_type` (misal: `Coal`, `Nickel`, `Gold`, `Copper`), `company_type` (`public`, `private`), `q`, `limit`, `offset`.

### 1.2 Detail Operasional Tambang (`/v2/mining/companies/{slug}/`)
* **Endpoint**: `GET /v2/mining/companies/{slug}/`
* **Deskripsi**: Rincian kegiatan operasi, jenis izin tambang, status IUP/IUPK, dan jumlah *site* aktif.

### 1.3 Keuangan Perusahaan Tambang (`/v2/mining/companies/financials/{slug}/`)
* **Endpoint**: `GET /v2/mining/companies/financials/{slug}/`
* **Deskripsi**: Laporan keuangan tahunan spesifik sektor pertambangan dalam denominasi **USD Millions**.
* **Parameter Query**: `year` (int).

### 1.4 Pohon Kepemilikan Korporasi Tambang (`/v2/mining/companies/ownership/{slug}/`)
* **Endpoint**: `GET /v2/mining/companies/ownership/{slug}/`
* **Deskripsi**: Struktur pohon kepemilikan holding perusahaan (*parent companies*) dan anak perusahaan tambang (*subsidiaries*) beserta persentase saham kepemilikannya.

### 1.5 Kinerja Operasional & Cadangan Tambang (`/v2/mining/companies/performance/{slug}/`)
* **Endpoint**: `GET /v2/mining/companies/performance/{slug}/`
* **Deskripsi**: Metrik operasional industri tambang: volume produksi, volume penjualan, *strip ratio* (rasio pengupasan tanah penutup), serta total estimasi sumber daya dan cadangan terbukti (*proven reserves*).

---

## 2. Komoditas & Perdagangan Global (Commodities & Trade)

### 2.1 Direktori Komoditas (`/v2/mining/commodities/`)
* **Endpoint**: `GET /v2/mining/commodities/`
* **Deskripsi**: Daftar seluruh komoditas yang dipantau harganya (Batu Bara, Nikel, Tembaga, Bauksit, Emas, Timah).

### 2.2 Riwayat Harga Komoditas (`/v2/mining/commodities/{commodity_name}/price/`)
* **Endpoint**: `GET /v2/mining/commodities/{commodity_name}/price/`
* **Deskripsi**: Data deret waktu harga acuan komoditas (bulanan/dwimingguan) hingga 3 tahun terakhir.

### 2.3 Destinasi Ekspor Tambang RI (`/v2/mining/exports/`)
* **Endpoint**: `GET /v2/mining/exports/`
* **Deskripsi**: Peringkat negara tujuan ekspor komoditas tambang Indonesia berdasarkan nilai total ekspor pada tahun tertentu.
* **Parameter Query**: `commodity_name`, `year`.

### 2.4 Destinasi Penjualan Emiten Tambang (`/v2/mining/sales-destination/{slug}/`)
* **Endpoint**: `GET /v2/mining/sales-destination/{slug}/`
* **Deskripsi**: Rincian distribusi pendapatan dan volume penjualan emiten tambang per negara tujuan ekspor vs domestik (*Domestic Market Obligation* / DMO).

### 2.5 Data Komoditas Global (`/v2/mining/global-commodity/`)
* **Endpoint**: `GET /v2/mining/global-commodity/`
* **Deskripsi**: Perbandingan produksi global, cadangan dunia, dan arus perdagangan komoditas lintas negara.

---

## 3. Lokasi Tambang, Cadangan & Produksi (Sites & Reserves)

### 3.1 Direktori Site Tambang (`/v2/mining/sites/`)
* **Endpoint**: `GET /v2/mining/sites/`
* **Deskripsi**: Daftar konsesi tambang aktif dengan filter lokasi provinsi, jenis komoditas, dan kapasitas produksi.

### 3.2 Detail Lokasi & Geospasial Tambang (`/v2/mining/sites/{slug}/`)
* **Endpoint**: `GET /v2/mining/sites/{slug}/`
* **Deskripsi**: Informasi terinci site tambang mencakup titik koordinat latitude/longitude dan taksiran cadangan di lokasi tersebut.

### 3.3 Indeks Sumber Daya & Cadangan per Provinsi (`/v2/mining/resources-reserves/`)
* **Endpoint**: `GET /v2/mining/resources-reserves/`
* **Deskripsi**: Matriks ketersediaan data cadangan mineral/batu bara per provinsi di Indonesia.

### 3.4 Rincian Cadangan Provinsi (`/v2/mining/resources-reserves/{province}/`)
* **Endpoint**: `GET /v2/mining/resources-reserves/{province}/`
* **Deskripsi**: Rincian cadangan terukur, terindikasi, dan tereka per jenis mineral di provinsi terkait.

### 3.5 Total Produksi Nasional Komoditas (`/v2/mining/total-production/`)
* **Endpoint**: `GET /v2/mining/total-production/`
* **Deskripsi**: Total produksi nasional komoditas tahunan dan persentase perubahan tahunan (YoY).

---

## 4. Kontrak Jasa, Izin & Lelang IUP (Contracts & Licenses)

### 4.1 Kontrak Jasa Penambangan (`/v2/mining/contracts/`)
* **Endpoint**: `GET /v2/mining/contracts/`
* **Deskripsi**: Hubungan kontrak aktif antara pemilik konsesi tambang (*mine owner*) dengan kontraktor jasa penambangan (misal: keterkaitan emiten dengan PAMA, BUMA, dll.).

### 4.2 Izin Usaha Pertambangan / IUP (`/v2/mining/licenses/`)
* **Endpoint**: `GET /v2/mining/licenses/`
* **Deskripsi**: Database perizinan IUP/IUPK resmi dari portal Ditjen Minerba ESDM dengan filter status, komoditas, lokasi, dan masa berlaku.

### 4.3 Lelang Wilayah Izin Usaha Pertambangan (`/v2/mining/license-auctions/`)
* **Endpoint**: `GET /v2/mining/license-auctions/`
* **Deskripsi**: Daftar lelang wilayah izin usaha pertambangan (WIUP) yang diselenggarakan pemerintah.

### 4.4 Detail Lelang WIUP (`/v2/mining/license-auctions/{wiup_code}/`)
* **Endpoint**: `GET /v2/mining/license-auctions/{wiup_code}/`
* **Deskripsi**: Rincian tahapan lelang konsesi tambang, jadwal, dan daftar peserta lelang yang lolos kualifikasi.
