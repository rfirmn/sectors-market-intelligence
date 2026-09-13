# Judging, kritik rancangan, dan simulasi Market State Engine

Tanggal: 13 September 2026. Ruang lingkup: `engine_mathematics_and_logic.md`, PRD,
implementasi engine, tes, cache lokal, literatur primer, dan eksperimen sintetis.
Bahasa penilaian: riset investasi IDX nonfinansial; bukan rekomendasi membeli saham tertentu.

## 1. Putusan

**Kekhawatiran bahwa development belum solid beralasan.** Fondasi perangkat lunaknya
cukup rapi untuk MVP, tetapi argumentasi ekonominya dan bukti validasinya tertinggal
dari tingkat kepastian yang disampaikan dokumentasi. Median/MAD adalah pilihan
baseline yang masuk akal; kelemahan terbesarnya justru berada pada definisi data,
perbandingan periode, makna discrepancy, dan belum adanya pengujian prediktif.

Sistem ini saat ini paling tepat diposisikan sebagai **penyaring prioritas riset
berdasarkan ketidaksesuaian perubahan fundamental dan harga relatif**. Ia belum
mengestimasi nilai intrinsik, ekspektasi yang tersirat dalam harga, probabilitas
keberhasilan, ataupun expected return. Loop numerical → linguistic → numerical
membantu memeriksa klaim memo, tetapi tidak membuktikan bahwa harga kelak konvergen.

Penilaian berikut adalah rubric saya atas kondisi sebelum perbaikan, bukan skor
resmi hackathon atau angka hasil model statistik:

| Aspek | Bobot | Nilai /10 | Kontribusi | Alasan |
|---|---:|---:|---:|---|
| Fokus produk dan pemisahan modul | 20 | 8 | 16 | Universe nonfinansial dan pipeline sederhana jelas |
| Kebenaran kontrak/perhitungan data | 20 | 5 | 10 | TTM missing-as-zero, periode, dan fallback bermasalah |
| Ketahanan dan interpretasi statistik | 20 | 5 | 10 | MAD masuk akal; skala nol dan klaim probabilitas tidak |
| Bukti kinerja prediktif/investabilitas | 25 | 1 | 2,5 | Belum ada backtest point-in-time, biaya, atau forward test |
| Reproduksibilitas dan kejujuran klaim | 15 | 6 | 9 | Baseline 84 tes lulus; sebagian klaim empiris tidak terlacak |
| **Total** | **100** | | **47,5/100** | **Konsep layak dilanjutkan; belum layak diklaim sebagai alpha engine** |

Ini bukan alasan membongkar seluruh arsitektur. Perbaikan validitas data dan
pelaporan ketidakpastian memberi manfaat lebih jelas daripada mengganti MAD
dengan estimator yang lebih rumit hanya demi kebaruan.

## 2. Temuan yang paling menentukan

### 2.1 Discrepancy belum berarti undervaluation

Formula PRD yang benar-benar dievaluasi adalah:

```text
F = (z_revenue_growth + z_earnings_growth + z_margin_change) / 3
D = F - z_price_return
candidate: D > 1.0; HIGH: D > 1.5
```

ROE tidak termasuk formula ini; PE/PB hanya informasional. Maka `D` tidak memakai
harga relatif terhadap arus kas/laba/aset sebagai ukuran murah. Price return
yang buruk tidak identik dengan valuasi murah. Contoh `F=-1`, `P=-3` menghasilkan
`D=2`: label HIGH meskipun fundamental relatif memburuk. `F=2`, `P=1` menghasilkan
`D=1` dan tidak lolos aturan strict `>1`, walaupun fundamental kuat.

Jika produk memang ingin menemukan perbaikan fundamental, usulkan gate `F>0`
di discovery sebagai hipotesis eksplisit. Ini tetap hanya perbaikan relatif:
fundamental absolut dapat turun ketika subsektor turun lebih tajam. Tampilkan
komponen F dan P berdampingan serta counter-thesis siklus, dilusi, utang, dan capex.
Belum ada implementasi discovery operasional yang perlu diganti; modulnya masih
placeholder. Gate ini dicatat sebagai spesifikasi untuk implementasi berikutnya.

### 2.2 Tanggal fiskal, publikasi, harga, dan waktu komputasi berbeda

Laporan per 30 Juni tidak berarti informasi tersebut diketahui investor pada
30 Juni. `data_timestamp=datetime.now()` hanya waktu komputasi. Cache juga bisa
dipakai ulang setelah permintaan live gagal. Backtest yang memakai laporan terbaru
atau revisi terbaru seolah tersedia pada tanggal fiskalnya terkena look-ahead bias.

Perbaikan sekarang menyamakan periode observasi dalam normalisasi. Pekerjaan
berikutnya masih memerlukan `period_end`, `published_at`, `retrieved_at`, `as_of`,
status cache stale, dan vintage/restatement. Cohort periode yang sama belum berarti
point-in-time valid. Jangan membangun backtest dari cache snapshot terbaru lalu
menganggapnya sejarah informasi investor.

### 2.3 YoY, QoQ, dan TTM harus memiliki kontrak yang tegas

YoY dan QoQ mengukur horizon berbeda. Metadata `growth_method` saja tidak cukup
ketika nilainya tetap masuk satu distribusi. YoY juga hanya mengurangi musiman;
pergeseran Ramadhan, tahun fiskal, akuisisi, dan perubahan segmen tetap relevan.

Implementasi awal mensyaratkan lima baris untuk mencari YoY, padahal dua observasi
dengan periode yang tepat cukup. Pencocokan ±1 bulan bisa menerima periode salah.
Empat baris terbaru tidak otomatis berarti empat kuartal berurutan, unik, dan
lengkap. `None` yang diganti nol mengubah laba TTM tanpa dasar ekonomi.

Contoh laba empat kuartal `[10, None, 10, 10]`: versi awal menghasilkan 30;
yang diketahui sebenarnya hanya tiga kuartal. TTM harus unavailable. Sebaliknya
`[10, -10, 10, -10]` menghasilkan nol yang valid, sehingga ROE nol valid jika
ekuitas positif. PB dan margin kuartal terbaru tidak perlu menunggu empat kuartal.

**Masih perlu verifikasi provider:** apakah setiap field flow adalah standalone
quarter atau kumulatif YTD. Jika YTD, Q2 standalone = H1 − Q1 dan Q4 = FY − 9M,
dengan tahun, mata uang, konsolidasi, dan revisi konsisten. Neraca tidak boleh
didiferensiasi. Jangan melakukan konversi otomatis berdasarkan tebakan besar angka.

ROE dengan ekuitas akhir periode adalah penyederhanaan yang tetap dipertahankan
untuk menjaga baseline. Average equity lebih representatif untuk return terhadap
modal selama periode; pastikan laba attributable-to-parent dipasangkan dengan
equity attributable-to-parent. Cache ASII memiliki `total_equity` dan
`stockholders_equity`, sehingga definisi denominator perlu diselesaikan sebelum
menambah model profitability.

### 2.4 Growth dari basis laba negatif bukan persentase pertumbuhan biasa

`(current-previous)/abs(previous)` menjaga tanda perbaikan rugi ke laba, tetapi
tidak membuatnya sebanding secara ekonomi dengan pertumbuhan perusahaan profitable.
Rugi −10 menjadi −2 memberi +80%, padahal perusahaan masih rugi. Ambang denominator
Rp1 juta hanya guard aritmetika berasumsi unit IDR, bukan filter kapitalisasi,
likuiditas, atau kualitas laba.

Pisahkan flag `loss_to_profit`, `still_loss`, `profit_to_loss`, basis mendekati nol,
dan extraordinary items pada tahap challenge. Kandidat eksperimen:
perubahan laba dibagi average assets atau revenue periode pembanding. Formula
tersebut mengubah makna sinyal, sehingga perlu versioning dan validasi tersendiri.

### 2.5 Tiga komponen fundamental bisa menghitung informasi yang sama berulang

Revenue growth, earnings growth, dan margin change berkorelasi secara akuntansi.
Bobot sama tidak menghasilkan tiga bukti independen. Selain itu F merata-ratakan
tiga skor, sedangkan harga masuk dengan koefisien −1; skala dan korelasi
menentukan dominasi komponen, bukan jumlah nama metrik.

Untuk covariance matrix Σ dan `a=(1/3,1/3,1/3,-1)`, `Var(D)=a'Σa`.
Bahkan bila keempat z independen dengan variance satu, `Var(D)=4/3`, sehingga
standard deviation D sekitar 1,155, bukan satu. Di bawah asumsi normal ideal itu,
`D>1` memiliki tail probability sekitar 19,3%, bukan tail 1σ sekitar 15,9%.
Ini ilustrasi analitis, bukan prediksi proporsi kandidat IDX. Korelasi dan ekor
berat membuat kalibrasi makin berbeda. Threshold sekarang adalah aturan triase.

## 3. Audit statistik: yang dipertahankan dan yang dikoreksi

Median/MAD berguna saat ekor berat/outlier mendistorsi standard deviation.
Pilihan estimator harus sesuai bentuk distribusi; MAD bukan estimator paling
efisien pada semua kondisi. [NIST, Measures of Scale](https://itl.nist.gov/div898/handbook/eda/section3/eda356.htm).

`1.4826` memberi normal consistency asimptotik. Ini tidak membuktikan unbiasedness
pada n kecil, normalitas skor, probabilitas laba, atau ambang gabungan “1σ”.
Breakdown point mendekati 50% juga bukan janji bahwa 49% data rusak aman.

Winsorizing 1%/99% dengan interpolasi sangat lemah untuk maksimum tunggal pada
subsektor kecil. Pada `[1,2,3,4,1000]`, p99 = `0.04×4 + 0.96×1000 = 960.16`:
96% bobot masih pada maksimum. Ini mengurangi 39,84, bukan menghapus outlier.
Dengan n=8, bobot maksimum masih 93%; n=15 86%; n=30 71%; n=60 41%, selama
persentil itu masih menginterpolasi dua order statistic tertinggi.

Implementasi menggunakan median/MAD dari nilai winsorized, tetapi numerator
`x_i` mentah. Ini sah sebagai pilihan deteksi outlier; tidak sah bila dijelaskan
sebagai pembatas kontribusi individual. Pada contoh n=5 tadi, median=3,
MAD=1, z maksimum sekitar **672,47**. Bahkan numerator clipped masih sekitar
**645,60**. Jadi sekadar menyamakan numerator dengan winsorized belum cukup
untuk menjamin komposit stabil.

Fallback skala `0.01×abs(median)` lebih bermasalah: `[1,1,1,2,3]` memiliki
MAD nol dan memberi skor 100 pada nilai 2. Setelah semua nilai dikurangi satu,
`[0,0,0,1,2]` memberi skor nol pada semua observasi. Informasi relatif tidak
berubah, tetapi skor berubah drastis. Fallback itu dihapus; kasus degenerate
sekarang menghasilkan `None` dan status eksplisit.

`n<3 → 0` juga dihapus. Nol berarti posisi pusat yang terukur; missing berarti
posisi tidak dapat diukur. `n=3..7` masih dihitung untuk menjaga baseline, tetapi
ditandai `low_sample`. Angka delapan adalah label kehati-hatian engineering,
bukan batas ilmiah yang divalidasi simulasi atau izin otomatis menjalankan trading.

Untuk satu metrik, `z=(x-location)/scale` dengan scale positif mempertahankan
urutan x. Median/MAD, mean/SD, atau Qn tidak bisa berbeda Spearman terhadap x
kecuali terdapat ties, clipping, atau cohort berbeda. Perubahan estimator baru
berpengaruh pada threshold, magnitudo, dan ranking **gabungan lintas metrik**.

## 4. Model pembanding dan pilihan pengembangan

Telaah rinci beserta sumber primer ada di [perbandingan model finansial](research/financial_model_comparison.md).
Perbandingan ini tidak menyamakan factor risk model, screener, dan valuation model.

| Model | Yang berguna | Keterbatasan untuk proyek ini | Keputusan |
|---|---|---|---|
| Fama–French FF5 | Kontrol market, size, value, profitability, investment | Perlu faktor lokal dan time series; bukan estimasi harga wajar | Benchmark evaluasi setelah data sejarah tersedia |
| q-factor | Profitabilitas dibaca bersama investasi/aset | Kebutuhan kalender publikasi dan portofolio faktor | Referensi mekanisme, belum perlu engine faktor |
| Piotroski F-Score | Checklist kesehatan keuangan yang mudah dijelaskan | Aslinya pada kelompok value/high book-to-market; banyak field | Checklist opsional, jangan jadi skor universal |
| Magic Formula | Menggabungkan murah dan produktivitas modal | Definisi EV/modal, perusahaan rugi, dan cyclicality krusial | Baseline transparan untuk pengujian value-quality |
| Gross profitability/assets | Ukuran quality yang sederhana dan relatif dekat operasi | Definisi COGS/aset lintas subsektor perlu konsisten | Kandidat eksperimen setelah validitas data |
| Sloan accruals / cash conversion | Menguji apakah pertumbuhan laba didukung kas | Periode CFO dan laba harus sama; formula proxy perlu disebut | Prioritas fitur challenge berikutnya |
| Momentum | Menguji alternatif bahwa harga mengandung informasi lanjutan | Return satu bulan bukan definisi momentum akademik | Benchmark yang berlawanan dengan leg kontrarian |
| PEAD / earnings surprise | Dekat tesis informasi laba belum tercermin | Butuh event date, unexpected earnings, dan event return | Eksperimen sesudah point-in-time tersedia |
| Reverse DCF / expectations investing | Menurunkan ekspektasi operasi dari harga | Banyak asumsi; satu harga tidak mengidentifikasi growth/margin/WACC unik | Sensitivity tool untuk kandidat final |

Model populer tidak otomatis mati dan model kurang dikenal tidak otomatis lebih
baik. Bukti publication decay dan replikasi memberi alasan untuk menguji hasil
di luar sampel dan setelah friksi, bukan untuk memilih model berdasarkan usia.
[McLean–Pontiff](https://doi.org/10.1111/jofi.12365),
[Hou–Xue–Zhang](https://academic.oup.com/rfs/article/33/5/2019/5236964).

Kandidat fitur paling relevan adalah **kualitas laba**, bukan tambahan estimator
skala. Proxy `(NI_TTM − CFO_TTM)/average_assets` dapat menjadi counter-evidence,
dengan catatan ia bukan replikasi persis seluruh definisi accrual paper Sloan.
Tidak ada threshold universal HIGH_ACCRUAL yang sudah terbukti untuk IDX dalam
pekerjaan ini. Tampilkan nilai dan konteks peer lebih dahulu.

## 5. Simulasi yang dijalankan

Eksperimen Monte Carlo, konfigurasi, standard error, dan tabel lengkap disimpan
di [hasil simulasi](research/simulation_results.md), dengan
[JSON hasil](research/simulation_results.json) dan
[skrip reproduksi](../scripts/simulate_scoring_methods.py).

Baseline legacy dibekukan di skrip supaya koreksi produksi tidak mengubah baseline
secara diam-diam. Eksperimen memisahkan estimasi lokasi/skala, pergeseran skor
observasi bersih, perubahan keputusan threshold, dan pemulihan top kandidat
pada komposit sintetis. Nilai “truth” berasal dari proses pembangkitan data,
bukan return saham masa depan yang diamati.

Qn harus memakai order statistic `k=h(h−1)/2`, `h=floor(n/2)+1`, atas seluruh
jarak pasangan `|x_i−x_j|`. Konstanta asimptotik yang lebih tepat sekitar 2,219144;
faktor finite-sample harus dibedakan dari konstanta itu. Implementasi referensi:
[source robustbase](https://raw.githubusercontent.com/cran/robustbase/master/R/qnsn.R).
Kalibrasi pada data evaluasi yang sama akan menguntungkan Qn secara tidak adil.

Rank-normal scores membatasi ekstrem pada ukuran sampel tertentu, tetapi
menghilangkan sebagian informasi magnitudo dan memiliki resolusi terbatas ketika
n kecil. Shrinkage dapat menstabilkan subsektor tipis jika peer sektor memang
exchangeable; pooling bisa bias ketika struktur subsektor berbeda. Kemenangan
pada simulasi dengan sektor homogen tidak dapat digeneralisasi ke sektor nyata.

`log1p(growth)` hanya valid untuk growth > −1; loss transitions dengan penyebut
absolut dapat melampaui domain itu. Untuk rasio positif yang sangat skewed,
transformasi log masuk akal sebagai kandidat. Signed-log/asinh mempunyai makna
dan parameter skala berbeda, sehingga jangan diterapkan massal pada seluruh rasio.

**Ringkasan numerik Monte Carlo:** seed `20260913`, 200 repetisi untuk masing-masing
dari 135 sel eksperimen (27.000 skenario-replikasi), enam metode, ukuran subsektor
5/8/15/30/60. Tabel berikut memakai eksperimen komposit enam subsektor dan
mengagregasi lima ukuran sampel serta tiga skenario noise dengan bobot sama.
Angka adalah **persentase recovery anggota latent top-10%**, bukan return investasi.

| Metode | Tanpa kontaminasi | Kontaminasi nominal 10% | Kontaminasi nominal 20% |
|---|---:|---:|---:|
| Legacy raw/MAD | 56,90% | 16,50% | 13,63% |
| Clipped MAD | 58,25% | 16,96% | 13,60% |
| Qn asimtotik | 61,13% | 16,07% | 13,40% |
| Qn terkoreksi finite-sample | 61,13% | 16,07% | 13,40% |
| Normal-score rank | 62,68% | 38,99% | 28,98% |
| Shrink sektor | 67,04% | 17,95% | 14,06% |

Pada kontaminasi nominal 20%, perbaikan recovery rank-normal terhadap legacy
adalah **15,35 poin persentase ± 0,29 pp SE** dari perbandingan berpasangan pada
seed yang sama. SE ini mengukur ketidakpastian Monte Carlo pada grid/DGP tetap,
bukan ketidakpastian transfer ke IDX. Bahkan metode terbaik masih hanya
memulihkan sekitar 29% anggota kelompok terbaik pada skenario itu.

Kontaminasi adalah per metrik: empat kesempatan rusak per perusahaan, bukan
label bahwa persis 20% perusahaan memiliki data rusak. Jumlah kontaminan dibulatkan
ke integer; misalnya n=5 pada nominal 10% mempunyai satu kontaminan, yaitu 20% aktual.
Karena itu tabel nominal tidak boleh dibaca sebagai rate aktual yang identik.

Qn terkoreksi dan asimtotik memiliki ranking sama karena setiap subsektor dan
metrik memiliki n yang sama pada satu replikasi; koreksi memberi multiplier
positif bersama. Perbedaannya terlihat pada estimasi skala/threshold di eksperimen
satu metrik, bukan pada urutan komposit ini. Pada data nyata dengan missingness
dan n tidak seragam, kesamaan itu tidak dijamin.

Untuk eksperimen satu metrik pada nominal 10% dan sektor selaras, drift absolut
skor observasi bersih adalah 0,8958 pada legacy, 0,3092 clipped MAD, dan 0,1503
shrink sektor. Dua batas interpretasi penting: clipped MAD juga mengubah fallback
MAD nol, sehingga manfaatnya bukan efek clipping murni; shrinkage menerima 4n
observasi eksternal yang selalu bersih dan mengencerkan kontaminasi sekitar lima
kali. Keuntungan informasi tambahan itu tidak boleh dipasarkan sebagai kemenangan
estimator semata. Di eksperimen komposit, semua kelompok observed dapat terkontaminasi.

**Keputusan riset:** rank-normal adalah kandidat terbaik untuk diuji lanjut pada
komposit yang rentan gross errors; shrinkage perlu pengujian heterogenitas dan
kualitas pool; Qn layak sebagai pembanding skala, belum terbukti unggul umum.
Tidak ada kandidat yang memperoleh bukti alpha atau kelayakan promosi produksi
hanya dari eksperimen ini. Perubahan kode final tetap koreksi validitas yang
diuraikan berikut.

## 6. Perubahan kode yang diterapkan

Versi metodologi sekarang `2026-09-13-validity-v2`. Perubahan memprioritaskan
kebenaran data dan pengungkapan status; estimator alternatif tetap eksperimen.

| Area | Perubahan | Perilaku yang diharapkan |
|---|---|---|
| Metrics | YoY dicari dari pasangan periode, QoQ hanya kuartal bersebelahan | Data sparse tidak otomatis salah horizon |
| TTM | Empat kuartal lengkap, unik, berurutan, laba finite | Missing tidak dianggap nol; ROE nol tetap valid |
| Rasio level | Margin/PB dihitung tanpa syarat empat kuartal | Riwayat pendek tidak menghilangkan rasio yang sah |
| Angka | Tolak NaN/inf/non-numeric/bool dan hasil tidak finite | Satu input rusak tidak meracuni statistik peer |
| Normalisasi | MAD nol dan sampel tidak cukup → None | Tidak ada kepastian palsu dari angka nol/fallback median |
| Comparability | Growth YoY-only; cohort periode per keluarga metrik | Raw QoQ tetap tampil; tidak dicampur ke distribusi YoY |
| Provenance | Status distribusi, periode dipilih, alasan pengecualian | Coverage dan ketidakpastian dapat diaudit |
| Dokumentasi | Koreksi klaim σ, anti-outlier, dan validasi 100% | Klaim sesuai bukti yang tersedia |

Pilihan cohort terbesar menghemat implementasi dan mempertahankan profil yang
dapat dibaca. Tradeoff-nya: emiten pada periode lain tidak mendapat peer_z untuk
metrik tersebut, bahkan bila data mentah tersedia. Tie diputuskan ke periode
terbaru secara deterministik. Cohort dapat berubah ketika batch laporan baru
masuk; membership dan periode perlu disimpan pada setiap snapshot evaluasi.

Formula baseline dan numerator mentah dipertahankan untuk memisahkan koreksi
validitas dari perubahan hipotesis investasi. Ini bukan rekomendasi membiarkan
skor ekstrem langsung menjadi order trading. Modul discovery, liquidity gating,
dan backtest operasional belum tersedia. Consumer berikutnya wajib menolak
discrepancy ketika salah satu dari tiga growth z atau price z unavailable;
jangan average hanya metrik tersedia karena akan mengubah bobot antarperusahaan.

## 7. Rancangan validasi dan development berikutnya

Urutan pekerjaan sebaiknya menjadi **kontrak data → validitas cohort → baseline
discovery → challenge kualitas laba → evaluasi point-in-time → presentasi memo**.

| Prioritas | Pekerjaan | Kriteria selesai |
|---|---|---|
| P0 | Verifikasi standalone vs YTD, currency, unit, konsolidasi | Contoh laporan sumber direkonsiliasi per field; kontrak tertulis |
| P0 | Publication time, vintage, cache freshness, price window | Setiap snapshot mempunyai information cutoff yang dapat diaudit |
| P0 | Discovery lengkap tanpa imputasi skor | F, P, D, missingness, cohort, versi, dan alasan eligibility tersimpan |
| P1 | Corporate actions dan investabilitas | Adjusted/total return terverifikasi; suspensi, stale quote, traded value terlihat |
| P1 | Challenge cash conversion/accrual | NI dan CFO periode sama; counter-evidence numerik ditampilkan |
| P1 | Baseline comparison berjalan | Model sederhana dan kandidat baru diuji pada split waktu identik |
| P2 | Qn/rank/shrinkage/log feature | Hanya dipromosikan jika manfaat stabil di data evaluasi yang belum dilihat |
| P2 | Reverse DCF memo | Sensitivitas asumsi dan rentang ekspektasi; tidak satu target price palsu presisi |

Untuk IDX, laporkan ADV/traded value, proporsi hari aktif, free float bila ada,
konsentrasi posisi, spread proxy, dan riwayat suspensi. Ukur kapasitas sebagai
fraksi turnover pasar, bukan sekadar jumlah saham lolos. ARA/ARB berulang dapat
menimbulkan kesulitan eksekusi; jangan mengasumsikan transaksi tersedia pada close.
UMA adalah peringatan aktivitas tidak biasa, bukan bukti bahwa emiten melakukan
manipulasi. Status tersebut harus memicu pemeriksaan bukti, bukan label
“gorengan” otomatis. [Penjelasan resmi BEI](https://www.idx.id/id/investor/pantau/).
Ambang dan mekanisme bursa dapat berubah; jangan hardcode aturan tahun tertentu
tanpa tanggal berlaku dan rujukan resmi.

Protokol evaluasi yang disarankan:

1. Bekukan universe historis termasuk delisted dan gagal, formula, missing policy,
   horizon return (misalnya 1/3/6 bulan), rebalancing, dan seluruh kandidat metode
   sebelum membuka holdout. Jangan memilih hanya subsektor atau ticker demo sukses.
2. Gunakan training/validation/test yang berurutan secara waktu. Semua parameter
   shrinkage, transformasi, maupun threshold dipilih tanpa melihat test; sisakan
   forward paper portfolio. Return label yang tumpang tindih perlu purge/gap sesuai
   horizon agar tidak melintasi split training dan test.
3. Entry paling cepat pada kesempatan eksekusi setelah publikasi informasi.
   Gunakan vintage yang tersedia ketika itu, corporate-action-adjusted return,
   delisting treatment, biaya, slippage, suspensi, dan constraints kapasitas.
4. Bandingkan baseline D, F saja, price leg saja, value-quality sederhana, dan
   kandidat robust terpilih. Ablasi ini menguji apakah sinyal gabungan menambah
   informasi atau hanya membungkus short-term reversal.
5. Laporkan rank IC terhadap forward return, top-quantile spread, return net,
   turnover, drawdown, coverage, dan sensitivitas microcap. Untuk IDX long-only,
   hitung portofolio implementabel; long-short akademik hanya diagnostik.
6. Interval ketidakpastian dihitung lintas tanggal/batch, misalnya block bootstrap,
   agar korelasi saham dalam hari yang sama tidak dianggap observasi independen.
   Laporkan seluruh spesifikasi yang dicoba dan hasil buruknya, bukan hanya pemenang.

Kriteria promosi: peningkatan terhadap baseline konsisten pada holdout dan setelah
biaya, tidak didominasi satu subsektor atau microcap illiquid, coverage masuk akal,
serta interval estimasi tidak terlalu lebar untuk keputusan yang diambil. Jangan
mengganti ambang hanya karena tidak ada kandidat demo menarik; bila metode berubah,
buat versi baru dan evaluasi pada periode yang belum dipakai memilih perubahan.

## 8. Bukti, batas cakupan, dan cara membaca keluaran

Baseline tes: **84 passed** sebelum perubahan. Tes regresi baru memeriksa perilaku
data yang sebelumnya tidak tercakup; kelulusan tes memverifikasi implementasi pada
kasus yang diuji, bukan validitas prediktif model. Lihat hasil akhir verifikasi
di catatan akhir laporan ini.

Cache lokal yang terlihat mencakup satu emiten dengan empat kuartal ASII dan
sekumpulan endpoint pendukung; ini tidak cukup untuk backtest universe IDX atau
estimasi keuntungan strategi. Tidak ada klaim bahwa riset ini menjalankan
backtest historis saham Indonesia. Simulasi menguji sifat statistik di bawah
asumsi yang ditulis, sedangkan literatur memberi bukti dari sampel paper masing-masing.

Tabel lama 700 emiten/28 subsektor dan persentase 26,1%/18,9% tidak ditemukan
artefak reproduksinya dalam skrip/tes yang ditelusuri. Statusnya **belum
terverifikasi**, bukan dinyatakan palsu. Dokumen asal kini menandainya sebagai arsip.

Eksekusi memakai tiga agen dengan cakupan terpisah: Sol/high untuk literatur,
Sol/high untuk simulasi, Terra/high untuk audit data dan patch metrics. Agen utama
menangani statistik produksi, comparability, integrasi, dan judging. Pembagian
ini adalah proses development; tidak menambahkan arsitektur multi-agent ke produk.

Artefak pendukung:

- [Audit implementasi](research/implementation_audit.md): temuan lokasi kode dan status perbaikan.
- [Perbandingan model finansial](research/financial_model_comparison.md): sumber primer dan batas inferensi.
- [Hasil simulasi](research/simulation_results.md): konfigurasi, hasil, dan ketidakpastian.
- [Hasil JSON per sel](research/simulation_results.json): estimasi dan SE, bukan semua sampel per repetisi.
- [Dokumen matematika dengan koreksi](engine_mathematics_and_logic.md).

## 9. Verifikasi akhir

| Pemeriksaan yang dijalankan | Hasil |
|---|---|
| `.venv/bin/pytest -q` | **104 passed**, naik dari baseline 84; mencakup 20 kasus regresi tambahan |
| `.venv/bin/ruff check src tests scripts` | Lulus |
| `git diff --check` | Lulus |
| Compile modul engine dan skrip simulasi | Lulus |
| Fidelity baseline simulator terhadap kode `HEAD` sebelum patch | Identik pada tujuh dataset, termasuk ties dan MAD nol |
| Aritmetika cache ASII tanpa panggilan live | Growth revenue QoQ 0,73346%; earnings 14,23932%; ROE 10,27691%; PE 6,67319 |
| Periode harga cache ASII | 13 Agustus–11 September 2026, price return 2,29167%; bukan harga terkini |
| Peer score ASII sebagai kelompok tunggal | Seluruh skor `None`, sebagaimana kontrak baru |

Reproduksi simulasi dari root repository:

```bash
.venv/bin/python scripts/simulate_scoring_methods.py --repetitions 200 --seed 20260913
```

Perintah tersebut menghasilkan ulang JSON dan Markdown hasil simulasi. Tidak
memanggil API, tidak mengubah parameter produksi, dan hanya menggunakan standard
library. Hasil Monte Carlo dan tes tidak menggantikan backtest point-in-time;
validitas investasi tetap pekerjaan empiris berikutnya.
