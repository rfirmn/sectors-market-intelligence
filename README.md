# Market Intelligence Agent
## Sectors Hackathon 2026 — Track: Market Intelligence

> **Discover what matters. Research why. Challenge whether it survives.**

Sistem AI berbasis riset kuantitatif dan kualitatif yang mengidentifikasi **discrepancy (anomali/peluang)** antara performa fundamental emiten di Bursa Efek Indonesia (IDX) dengan valuasi pasarnya, memverifikasinya melalui bukti tekstual terkurasi dan data mikrostruktur bursa (*broker/foreign flow*), serta menghasilkan **Investment Memo interaktif** yang tahan uji numerik.

### Core Loop
$$\text{NUMERICAL (Engine)} \longrightarrow \text{LINGUISTIC (LLM/Research)} \longrightarrow \text{NUMERICAL (Challenge)}$$

---

### Setup Cepat

1. **Install Dependensi:**
   ```bash
   uv sync
   ```

2. **Konfigurasi Lingkungan:**
   Salin `.env.example` ke `.env` dan masukkan `SECTORS_API_KEY`:
   ```bash
   cp .env.example .env
   ```

3. **Jalankan Smoke Test Konektivitas:**
   ```bash
   uv run python scripts/smoke_test.py
   ```

4. **Jalankan Test Suite:**
   ```bash
   uv run pytest -v
   ```

---

### Dokumentasi Lengkap
* [Panduan Onboarding](docs/onboarding.md)
* [Spesifikasi Teknis & Formula](docs/project.md)
* [Timeline Pengembangan](docs/timeline.md)
* [Katalog Sectors API v2](docs/docs_sectors_api/README.md)
