# Implementation Plan — Hari 3: Opportunity Discovery & Priority Ranking Engine

## 1. Konteks & Tujuan

Hari 2 telah tuntas membangun pondasi matematika dan normalisasi statistik cross-sectional:
- Normalisasi subsektor via Winsorized Median & Scaled MAD ($k=1.4826$)
- 8 metrik finansial mentah + skor `peer_z` per emiten
- 84 unit/integration tests passing 100%, linter/pyright 0 errors

Fokus **Hari 3** adalah membangun otak deteksi dislokasi: **Opportunity Discovery & Priority Ranking Engine** (Task T3.1 s/d T3.5).
Sistem ini mengambil output `CompanyState` dari Hari 2, menghitung gap fundamental vs harga (*Variant Perception Detector*), menerapkan threshold yang dikunci *a priori* (1.0 dan 1.5), serta menyajikan daftar kandidat terurut (*Opportunity Feed*) untuk diteruskan ke tahap kualitatif (Hari 4).

---

## 2. Formalisasi Matematika & Aturan Bisnis

### A. Komposit Fundamental ($fundamental\_z$)
Sesuai [§6.2 project.md](project.md#L174):
$$fundamental\_z = \frac{1}{M} \sum_{m \in \mathcal{M}_{valid}} z(m)$$
di mana $\mathcal{M} = \{\text{revenue\_growth}, \text{earnings\_growth}, \text{margin\_change}\}$.

**Edge Cases & Rules:**
- $M = |\mathcal{M}_{valid}|$ adalah jumlah metrik yang tidak `None`.
- Syarat validitas: minimal 1 metrik fundamental harus valid ($M \ge 1$). Jika $M = 0$, maka $fundamental\_z = \text{None}$.
- Mengapa $M \ge 1$ diizinkan? Karena emiten tertentu (misalnya emiten siklikal atau baru IPO) mungkin memiliki salah satu metrik bernilai `None` (misal denominator nol pada kuartal sebelumnya), namun sinyal pertumbuhan lainnya tetap informatif.

### B. Komposit Harga ($price\_z$)
$$price\_z = z(\text{price\_return})$$
- Jika $z(\text{price\_return}) = \text{None}$, maka $price\_z = \text{None}$.

### C. Sinyal Dislokasi ($\text{discrepancy}$)
$$\text{discrepancy} = fundamental\_z - price\_z$$
- Jika $fundamental\_z = \text{None}$ atau $price\_z = \text{None}$, maka $\text{discrepancy} = \text{None}$ (emiten tidak dapat dievaluasi sebagai kandidat dislokasi).

### D. Klasifikasi Prioritas & Penguncian Parameter A Priori
Sesuai [§6.2 & §6.3 project.md](project.md#L180):
$$\text{priority\_score} = \text{discrepancy}$$

Kriteria klasifikasi:
$$\text{PriorityLevel} = \begin{cases} 
\mathbf{HIGH} & \text{jika } \text{discrepancy} > 1.5 \\ 
\mathbf{MEDIUM} & \text{jika } 1.0 < \text{discrepancy} \le 1.5 \\ 
\mathbf{NONE} & \text{jika } \text{discrepancy} \le 1.0 \text{ atau } \text{discrepancy is None}
\end{cases}$$

> **Disiplin Anti-Overfitting & Anti-Data-Snooping (§11 project.md):**
> Threshold `1.0` (kandidat) dan `1.5` (HIGH priority) dikunci secara eksplisit di awal sebelum kandidat demo dipilih. Interpretasinya berbasis statistik: dengan scaling factor $k=1.4826$ yang telah kita pasang di Hari 2, z-score setara dengan satuan deviasi standar $\sigma$.
> - $\text{discrepancy} > 1.0 \implies$ Fundamental mengungguli pergerakan harga sebesar $> 1\sigma$ relatif terhadap subsektornya.
> - $\text{discrepancy} > 1.5 \implies$ Dislokasi ekstrem $> 1.5\sigma$ relatif terhadap subsektornya (kandidat investigasi mendalam).

### E. Ranking & Tie-Breaking Deterministik
Kandidat yang lolos ($\text{discrepancy} > 1.0$) diurutkan dalam Opportunity Feed:
1. `priority_score` (discrepancy) secara menurun (DESC).
2. Jika ada skor identik (tie-break): urutkan berdasarkan `market_cap` DESC (emiten lebih likuid diutamakan), lalu `symbol` ASC untuk menjamin output selalu deterministik 100%.

---

## 3. Struktur File & Modul Baru

```
src/discovery/
├── __init__.py               # Public exports (OpportunityDiscoveryEngine, models)
├── models.py                 # Pydantic data contracts (DislocationScore, OpportunityCandidate, DiscoveryScanResult)
└── discovery_engine.py       # Engine perhitungan discrepancy & ranking

scripts/
└── run_discovery_scan.py     # Script runner untuk memindai universe / cache

tests/
└── test_discovery.py         # Test suite komprehensif untuk Hari 3
```

---

## 4. Desain Komponen Rinci

### Komponen 1: Data Contracts (`src/discovery/models.py`)

```python
from dataclasses import dataclass
from enum import Enum
from src.engine.models import CompanyState

class PriorityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    NONE = "NONE"

@dataclass
class DislocationScore:
    """Skor dislokasi fundamental vs harga."""
    fundamental_z: float | None = None
    price_z: float | None = None
    discrepancy: float | None = None
    priority_score: float | None = None
    priority_level: PriorityLevel = PriorityLevel.NONE
    fundamental_components_count: int = 0
    components_breakdown: dict[str, float | None] = None

@dataclass
class OpportunityCandidate:
    """Representasi emiten yang lolos filter discrepancy > 1.0."""
    company: CompanyState
    dislocation: DislocationScore
    rank: int = 0
    summary_headline: str = ""

@dataclass
class DiscoveryScanResult:
    """Hasil pemindaian universe/subsektor oleh Discovery Engine."""
    total_scanned: int
    total_evaluated: int
    total_candidates: int
    high_priority_count: int
    medium_priority_count: int
    candidates: list[OpportunityCandidate]
    discrepancy_distribution: dict[str, int]
    scan_timestamp: str
```

### Komponen 2: Discovery Engine (`src/discovery/discovery_engine.py`)

```python
class OpportunityDiscoveryEngine:
    """Variant Perception Detector.
    
    Menghitung dislocation score dan meranking emiten berdasarkan discrepancy.
    """
    HIGH_THRESHOLD: float = 1.5
    MEDIUM_THRESHOLD: float = 1.0

    def compute_dislocation(self, state: CompanyState) -> DislocationScore: ...
    def evaluate_candidates(
        self,
        companies: list[CompanyState],
        min_threshold: float = 1.0,
    ) -> DiscoveryScanResult: ...
```

### Komponen 3: Distribution Histogram (Kebutuhan UI Area 1)
Dashboard Area 1 di frontend membutuhkan visualisasi sebaran discrepancy seluruh emiten:
- `discrepancy < 0.0` (Price outperforms fundamentals)
- `0.0 <= discrepancy < 0.5` (Neutral alignment)
- `0.5 <= discrepancy < 1.0` (Mild divergence)
- `1.0 <= discrepancy < 1.5` (MEDIUM Opportunity)
- `discrepancy >= 1.5` (HIGH Opportunity)

Engine akan otomatis menghitung pembagian bin ini pada `DiscoveryScanResult.discrepancy_distribution`.

---

## 5. Verification Plan

### A. Unit Testing (`tests/test_discovery.py`)
1. **Perhitungan Fundamental Z**:
   - 3 metrik valid $\to$ rata-rata aritmetika tepat.
   - 2 metrik valid, 1 None $\to$ rata-rata 2 metrik yang ada.
   - 1 metrik valid, 2 None $\to$ nilai metrik tersebut.
   - 0 metrik valid $\to$ None.
2. **Perhitungan Price Z & Discrepancy**:
   - Kasus positif: fundamental_z = 1.8, price_z = 0.2 $\to$ discrepancy = 1.6 (HIGH).
   - Kasus medium: fundamental_z = 1.2, price_z = 0.0 $\to$ discrepancy = 1.2 (MEDIUM).
   - Kasus negatif: fundamental_z = -0.5, price_z = 0.8 $\to$ discrepancy = -1.3 (NONE).
   - Kasus None: salah satu None $\to$ discrepancy = None (NONE).
3. **Threshold Boundary Testing**:
   - `discrepancy = 1.000` $\to$ NONE (strictly $> 1.0$).
   - `discrepancy = 1.001` $\to$ MEDIUM.
   - `discrepancy = 1.500` $\to$ MEDIUM (strictly $> 1.5$).
   - `discrepancy = 1.501` $\to$ HIGH.
4. **Ranking & Sorting Order**:
   - Multiple candidate sorting descending by priority_score.
   - Tie-breaking deterministik.
5. **Distribution Histogram Bins**:
   - Verifikasi perhitungan bucket count.
6. **Full Scan Integration Test**:
   - Input list `CompanyState` hasil pipeline sintetis Hari 2 $\to$ verifikasi struktur `DiscoveryScanResult`.

### B. Live Universe Scan & Candidate Validation
Jalankan script `scripts/run_discovery_scan.py` menggunakan data cache Sectors API yang ada untuk mengidentifikasi 2–3 kandidat emiten nyata untuk demo Hari 4–7.

### C. Perintah Verifikasi
```bash
uv run pytest tests/test_discovery.py -v
make test
make lint
```
