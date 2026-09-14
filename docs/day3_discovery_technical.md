# Dokumentasi Teknis Hari 3
## Personalized Opportunity Discovery, Ranking, dan Universe Validation

**Methodology version:** `day3-personalized-discovery-v1`  
**Status:** implemented and covered by automated tests.

Hari kedua menghasilkan `CompanyState`: metrik mentah, peer-normalized z-score,
periode data, dan pengecualian normalisasi. Hari ketiga menggunakan objek itu
sebagai ground truth yang sama untuk semua pengguna. Yang berubah antar-pengguna
adalah mandate pencarian, bukan angka dasarnya.

## Alur sistem

```text
Sectors API / cache
       ↓
MarketStateEngine
       ↓  CompanyState lengkap per subsektor
Frozen reference cohorts
       ↓
Four lens evaluations
       ↓
ResearchMandate filters
       ↓
Weighted research_fit + deterministic order
       ↓
Opportunity Feed → Smart Research Hari 4
```

`DiscoveryEngine` adalah fungsi pure terhadap daftar `CompanyState` dan
`ResearchMandate`. Ia tidak melakukan HTTP request, tidak memanggil LLM, dan
tidak memodifikasi input. Perusahaan diurutkan berdasarkan `(subsector, symbol)`
sebelum evaluasi agar urutan input tidak memengaruhi hasil.

Implementasi utama:

| Komponen | Lokasi | Peran |
|---|---|---|
| Kontrak mandate dan result | [`src/discovery/models.py`](../src/discovery/models.py) | Pydantic validation, preset, filter, result schema |
| Mesin lensa dan ranking | [`src/discovery/discovery_engine.py`](../src/discovery/discovery_engine.py) | Cohort, skor, eligibility, ranking, funnel |
| Konteks market state | [`src/engine/models.py`](../src/engine/models.py) | Market cap, equity, tanggal, proxy aktivitas, provenance |
| Snapshot replay | [`src/api/snapshot_store.py`](../src/api/snapshot_store.py) | Hash, serialisasi, dan pembacaan snapshot |
| CLI | [`scripts/run_discovery_scan.py`](../scripts/run_discovery_scan.py) | `capture`, `search`, `validate` |

## Research Mandate

`ResearchMandate` memiliki preset `dislocation`, `growth`, `profitability`,
`value`, dan `custom`. Preset menetapkan bobot awal:

| Preset | Dislocation | Growth | Profitability | Value |
|---|---:|---:|---:|---:|
| `dislocation` | 100 | 0 | 0 | 0 |
| `growth` | 20 | 60 | 20 | 0 |
| `profitability` | 20 | 20 | 60 | 0 |
| `value` | 0 | 0 | 30 | 70 |

Bobot custom berada pada rentang 0–100, tidak boleh negatif, non-finite, atau
semuanya nol. Server menormalisasi bobot menjadi total 1. `display_mode`
(`guided`/`advanced`) hanya memengaruhi UI.

Filter mencakup include/exclude sector, subsector, dan symbol; rentang raw
revenue growth, earnings growth, operating margin, margin change, PB, price
return, market cap; serta usia data. Rentang minimum dan maksimum bersifat
inklusif. Pilihan dalam satu daftar memakai OR, kategori berbeda memakai AND,
dan exclude selalu menang.

Satuan request:

- growth, return, margin: rasio desimal (`0.15` = 15%);
- margin change: rasio desimal (`0.02` = 2 percentage points);
- PB: kelipatan;
- market cap: IDR.

PE dan ROE belum digunakan untuk ranking karena basis TTM sumber perlu jaminan
semantik tambahan. Proxy aktivitas transaksi juga tidak aktif sebagai filter
karena unit volume Sectors belum diverifikasi.

## Cohort dan kualitas bukti

Mesin membentuk cohort dari perusahaan dengan seluruh input wajib lensa tersedia,
finite, dan memiliki periode yang sama dalam subsektor yang sama. Cohort dibuat
sebelum filter mandate. Dengan demikian, memasukkan watchlist atau filter sektor
tidak mengubah percentile perusahaan yang tersisa.

Jika tersedia beberapa periode, mesin memilih cohort terbesar; jika jumlah sama,
periode terbaru dipilih. Ukuran minimum:

- `standard`: minimal 8 perusahaan lengkap;
- `exploratory`: minimal 3 perusahaan lengkap;
- 3–7 diberi status `low_sample`;
- kurang dari 3 menjadi `insufficient_cohort`.

Delapan perusahaan valid untuk satu metrik tidak berarti ada delapan perusahaan
valid untuk irisan seluruh metrik lensa. Karena itu status cohort dihitung dari
complete case, bukan dari jumlah per-metrik secara terpisah.

## Empat lensa numerik

Percentile empiris menggunakan midrank:

\[
P(x)=\frac{\#(x_j<x)+0.5\#(x_j=x)}{N}
\]

Nilai sama memperoleh skor sama. Percentile adalah posisi relatif dalam peer
cohort, bukan probabilitas return.

### 1. Dislocation

\[
F=\frac{z_{revenue}+z_{earnings}+z_{margin}}{3}
\]
\[
D=F-z_{price}
\]
\[
s_D=P(D)
\]

Semua empat z-score wajib ada; tidak ada rata-rata parsial. Lensa match jika
`D > 1.0`. Label discrepancy tetap independen dari bobot:

- `HIGH`: `D > 1.5`;
- `MEDIUM`: `1.0 < D <= 1.5`;
- `NONE`: `D <= 1.0`;
- `NOT_EVALUABLE`: input wajib hilang atau invalid.

### 2. Growth

\[
G=\frac{z_{revenue}+z_{earnings}}{2}, \qquad s_G=P(G)
\]

Lensa match jika `G > 0` dan kedua raw growth positif. Flag
`earnings_growth_from_loss_base` tetap ditampilkan ketika pembanding laba
sebelumnya negatif.

### 3. Profitability

\[
s_P=\frac{P(operating\ margin)+P(margin\ change)}{2}
\]

Lensa match jika operating margin positif, margin change positif, dan `s_P > 0.5`.
Ini mengukur profitabilitas operasional relatif; bukan penilaian lengkap kualitas
bisnis.

### 4. Value relatif

\[
s_V=1-P(PB)
\]

PB harus positif, market cap dan latest equity harus tersedia serta positif/
non-negatif, dan tanggal financial serta market-cap harus tersedia. PB rendah
adalah posisi relatif dalam peer cohort; bukan bukti undervaluation.

## Ranking dan output

Untuk bobot efektif `w_l` dan skor lensa `s_l`:

\[
research\_fit=100\sum_l w_l s_l
\]

Kandidat harus lolos filter mandate, memiliki semua lensa dengan bobot positif
yang usable, dan match minimal satu lensa aktif. Lensa berbobot nol tidak
menghalangi kandidat ketika datanya hilang.

Urutan final:

1. `research_fit` menurun;
2. `symbol` menaik sebagai tie-break;
3. `max_per_subsector` diterapkan;
4. `top_k` diterapkan.

Result menyimpan `weighted_contributions`, `matched_lenses`, input setiap lensa,
cohort size, period, status, reasons, limitations, dan filter funnel. Feed kosong
adalah hasil valid; sistem tidak melonggarkan mandate secara otomatis.

## Snapshot, API, dan CLI

`SnapshotStore` menyimpan state JSON dengan ID hash konten, methodology version,
waktu capture, source mode, manifest, dan warnings. Snapshot adalah input replay,
bukan jaminan dataset point-in-time; tanggal laporan dan waktu publikasi tidak
disamakan.

Endpoint frontend-backend dijelaskan lengkap di
[`docs/api_contract.md`](api_contract.md). Ringkasnya:

- `GET /api/discovery/options` — preset, satuan, capability, snapshot IDs;
- `POST /api/opportunities/search` — mandate atas satu snapshot;
- `GET /api/overview?snapshot_id=...` — coverage dan histogram discrepancy.

CLI:

```bash
uv run python scripts/run_discovery_scan.py capture --mode fallback
uv run python scripts/run_discovery_scan.py search SNAPSHOT_ID --mandate mandate.json
uv run python scripts/run_discovery_scan.py validate SNAPSHOT_ID
```

Mode `live` mengambil API tanpa cache sebagai sumber utama, `cached` memakai
snapshot lokal, dan `fallback` mengizinkan fallback cache. Budget request dan
throttle dikonfigurasi melalui CLI; kegagalan API dicatat sebagai keterbatasan
capture, bukan disamarkan sebagai coverage penuh.

## Verifikasi

Tes Hari 3 berada di [`tests/test_discovery.py`](../tests/test_discovery.py) dan
[`tests/test_discovery_api.py`](../tests/test_discovery_api.py). Cakupannya:

- rumus dan arah percentile setiap lensa;
- batas discrepancy `1.0`/`1.5`;
- missingness, complete-case cohort, dan standard/exploratory;
- determinisme terhadap permutation dan display mode;
- perbedaan ranking antar-mandate atas ground truth yang sama;
- filter, bobot invalid, tie, dan batas subsektor;
- snapshot replay serta HTTP `404`/`422`.

Validasi terakhir: `126 passed`, Ruff lulus, compile check lulus.

Keterbatasan yang sengaja dipertahankan: scan penuh IDX dapat terkena rate limit
Sectors; hasil parsial wajib diberi label. Backtest point-in-time, event/news,
foreign flow, dan pencarian web masuk tahap berikutnya.
