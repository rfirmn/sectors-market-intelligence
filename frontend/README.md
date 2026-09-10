# Frontend UI — Market Intelligence Agent
## Sectors Hackathon 2026 (Hari 6 Scope)

Direktori ini dipersiapkan untuk antarmuka web modern (*Single Page Application*) yang mengonsumsi FastAPI backend di `http://localhost:8000/api`.

---

### Tiga Area Tampilan Wajib (§6.9 project.md):

1. **Area 1: Market Scan Overview (Dashboard Top Header)**
   * Menampilkan jumlah emiten yang discan di IDX.
   * Jumlah emiten setelah eliminasi sektor finansial.
   * Jumlah total *opportunity candidate* yang lolos threshold discrepancy ($z \ge 1.0$).
   * Distribusi kuartal terkini.

2. **Area 2: Opportunity Feed (Left/Top Rail)**
   * Kartu emiten teratas (1–3 ticker hasil scoring discrepancy).
   * Badge prioritas: `HIGH PRIORITY` ($z \ge 1.5$) atau `OPPORTUNITY CANDIDATE` ($z \ge 1.0$).
   * Key metrik ringkas: Revenue Growth, EPS Growth, Margin Change vs Price Return.

3. **Area 3: Interactive Memo View (Main Drill-down Area)**
   * Visualisasi alur berpikir AI secara bertahap:
     $$\text{Investigate} \longrightarrow \text{Mosaic Research} \longrightarrow \text{Flow Confirmation} \longrightarrow \text{Thesis} \longrightarrow \text{Numerical Challenge} \longrightarrow \text{Final Memo}$$
   * Komparasi skenario stres tes (Base, Conservative, Stress).
   * Inline data provenance & disclaimer kepatuhan non-advisory.

---

### Teknologi yang Direkomendasikan:
* **Framework**: React / Vite + TypeScript atau Tailwind / Vanilla Modern CSS.
* **Komunikasi Data**: REST API fetch ke backend FastAPI (`/api/overview`, `/api/opportunities`, `/api/memo/:symbol`).
