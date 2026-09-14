# Market Intelligence Agent
## Sectors Hackathon 2026 — Track: Market Intelligence

> **Discover what matters. Research why. Challenge whether it survives.**

Sistem AI berbasis riset kuantitatif dan kualitatif yang mengidentifikasi **discrepancy (anomali/peluang)** antara performa fundamental emiten di Bursa Efek Indonesia (IDX) dengan valuasi pasarnya, memverifikasinya melalui bukti tekstual terkurasi dan data mikrostruktur bursa (*broker/foreign flow*), serta menghasilkan **Investment Memo interaktif** yang tahan uji numerik.

---

### Core Loop Architecture
$$\text{NUMERICAL (Engine)} \longrightarrow \text{LINGUISTIC (LLM/Research)} \longrightarrow \text{NUMERICAL (Challenge)}$$

```
market-intelligence/
├── src/                            # Core Backend Pipeline & API
│   ├── client/                     # [Hari 1] Sectors API Client, Models & Local Snapshot Cache
│   ├── engine/                     # [Hari 2] Market State Engine (8 Metrik, Winsorizing, Median/MAD)
│   ├── discovery/                  # [Hari 3] Opportunity Discovery & Relational Ranking Engine
│   ├── research/                   # [Hari 4] Smart Research Engine (Mosaic Text Synthesis via Gemini)
│   ├── confirmation/               # [Hari 4] Confirmation Layer (Net Foreign Flow Direction)
│   ├── challenge/                  # [Hari 5] Numerical Challenge Engine (Deterministic Stress Testing)
│   ├── memo/                       # [Hari 5] Opportunity Memo Synthesizer (Markdown / JSON)
│   ├── api/                        # [Hari 5-6] FastAPI Server (Serving Endpoints for UI)
│   └── config.py                   # Pydantic Settings & Environment Manager
├── frontend/                       # [Hari 6] Modern Web UI (Dashboard 3 Area)
├── data/                           # Data Snapshots & Test Fixtures
│   ├── cache/sectors/              # File-based JSON Snapshots (Demo Reliability §6.10)
│   └── fixtures/                   # Golden demo fixtures
├── docs/                           # Dokumentasi & API Specs
│   ├── onboarding.md               # Orientasi cepat developer
│   ├── project.md                  # PRD & landasan matematis
│   ├── timeline.md                 # Jadwal sprint 7 hari
│   ├── walkthrough.md              # Rekam jejak progres proyek & checkpoint
│   ├── engine_mathematics_and_logic.md # Dokumentasi lengkap sistem, logika & matematika
│   └── docs_sectors_api/           # Katalog 70 endpoint Sectors API v2
├── scripts/                        # Utility & CLI tools (smoke_test.py, scan runner)
├── tests/                          # Automated Pytest suite with RESpx offline mocks
├── Makefile                        # Quick development commands
└── pyproject.toml                  # Dependencies & tooling configuration (uv)
```

---

### Perintah Cepat (Makefile)

| Command | Deskripsi |
|---|---|
| `make install` | Install semua dependensi via `uv` |
| `make test` | Jalankan seluruh unit test suite (`pytest`) |
| `make smoke-test` | Jalankan smoke test live konektivitas Sectors API |
| `make smoke-test-llm` | Jalankan live smoke test Gemini LLM |
| `make smoke-test-engine` | Jalankan cross-check live/cache Market State Engine pada ASII |
| `make dev-api` | Jalankan server backend FastAPI (`http://localhost:8000`) |
| `make lint` | Validasi kode dengan `ruff` dan `pyright` |
| `make format` | Otomatis rapikan format kode |

### Discovery snapshot dan pencarian

Hari 3 menyimpan market state sebagai snapshot lokal yang dapat diputar ulang. Pencarian hanya membaca snapshot sehingga perubahan watchlist atau filter tidak mengubah cohort peer atau angka dasar.

```bash
uv run python scripts/run_discovery_scan.py capture --mode fallback
uv run python scripts/run_discovery_scan.py search SNAPSHOT_ID --mandate mandate.json
uv run python scripts/run_discovery_scan.py validate SNAPSHOT_ID
```

`mandate.json` memakai `ResearchMandate` terstruktur dengan preset `dislocation`, `growth`, `profitability`, `value`, atau `custom`. Nilai growth, return, dan margin memakai rasio desimal (`0.15` berarti 15%). Hasil discovery adalah prioritas riset, bukan rekomendasi atau prediksi return.

---

### Memulai Pengujian

1. Masukkan API Key Sectors di `.env`:
   ```env
   SECTORS_API_KEY=your_actual_key_here
   ```

2. Jalankan Smoke Test:
   ```bash
   make smoke-test
   ```
