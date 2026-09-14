# Backend–Frontend API Contract — Day 3

Status: v1, read-only discovery API.

FastAPI generates the machine-readable schema at `/openapi.json` and the interactive reference at `/docs`. This document fixes the frontend-facing behavior and examples that are not obvious from the generated schema.

## Base behavior

- Base URL in development: `http://localhost:8000`.
- JSON is UTF-8. Symbols and enum values are lowercase in discovery payloads.
- Search reads an existing snapshot. It does not call Sectors, the LLM, or mutate the snapshot.
- Unknown fields are rejected with HTTP `422`.
- Unknown `snapshot_id` returns HTTP `404`.
- Numeric values are not probabilities and do not predict returns.

## Endpoints

### `GET /api/discovery/options`

Returns the controls that the frontend may render.

```json
{
  "presets": {
    "dislocation": {"dislocation": 100, "growth": 0, "profitability": 0, "value": 0},
    "growth": {"dislocation": 20, "growth": 60, "profitability": 20, "value": 0},
    "profitability": {"dislocation": 20, "growth": 20, "profitability": 60, "value": 0},
    "value": {"dislocation": 0, "growth": 0, "profitability": 30, "value": 70}
  },
  "units": {
    "growth_return_margin": "decimal ratio (0.15 = 15%)",
    "margin_change": "decimal ratio (0.02 = 2 percentage points)",
    "pb": "multiple",
    "market_cap": "IDR"
  },
  "capabilities": {
    "transaction_activity_filter": false,
    "pe_or_roe_ranking": false,
    "network_on_search": false
  },
  "snapshot_ids": ["b277dd2b4085a0ff"]
}
```

`capabilities.transaction_activity_filter` is false until the source volume unit is verified. PE and ROE remain informational in Day 3.

### `POST /api/opportunities/search`

Request body:

```json
{
  "snapshot_id": "b277dd2b4085a0ff",
  "mandate": {
    "version": "v1",
    "preset": "custom",
    "weights": {"dislocation": 50, "growth": 30, "profitability": 20, "value": 0},
    "filters": {
      "include_sectors": ["technology"],
      "exclude_symbols": ["EXAMPLE"],
      "revenue_growth": {"minimum": 0.0},
      "market_cap": {"minimum": 1000000000000}
    },
    "evidence_standard": "standard",
    "top_k": 10,
    "max_per_subsector": 3,
    "display_mode": "guided"
  }
}
```

`mandate` may omit all fields and defaults to the dislocation preset. Presets other than `custom` use fixed weights; sending different weights with such a preset is invalid. `custom` requires at least one positive, finite weight. Weight values are 0–100 and are normalized by the server.

Supported `preset`: `dislocation`, `growth`, `profitability`, `value`, `custom`.

Supported `evidence_standard`: `standard` (complete cohort ≥8) and `exploratory` (complete cohort ≥3; 3–7 is flagged `low_sample`).

Supported `display_mode`: `guided`, `advanced`. It changes presentation only and never changes ranking.

Lists are OR within the list and AND across filter categories. Exclude wins over include. Numeric ranges are inclusive. Growth, return, and margin use decimal ratios; PB is a multiple; market cap is IDR.

Response envelope:

```json
{
  "snapshot_id": "b277dd2b4085a0ff",
  "snapshot": {"captured_at": "2026-09-14T02:33:00Z", "source_mode": "cached", "warnings": []},
  "result": {
    "mandate": {},
    "effective_weights": {"dislocation": 1.0, "growth": 0.0, "profitability": 0.0, "value": 0.0},
    "snapshot_date": "2026-09-14",
    "candidates": [],
    "coverage": {},
    "funnel": {},
    "exclusions": {},
    "warnings": []
  }
}
```

`candidates` are ordered by descending `research_fit`, then ascending `symbol`. Each candidate includes `matched_lenses`, `weighted_contributions`, `lens_evaluations`, `discrepancy`, `discrepancy_label`, `evidence`, and `limitations`. `research_fit` is a prioritization score on a 0–100 scale, not a confidence score.

### `GET /api/overview?snapshot_id={id}`

Returns snapshot coverage and the discrepancy histogram used by the overview UI.

```json
{
  "snapshot_id": "b277dd2b4085a0ff",
  "captured_at": "2026-09-14T02:33:00Z",
  "source_mode": "cached",
  "universe": {
    "total_subsectors_scanned": 1,
    "total_companies_universe": 8,
    "total_with_data": 8,
    "total_excluded_financial": 0
  },
  "discrepancy_distribution": {
    "price_outperforms_fundamentals": 0,
    "neutral_alignment": 0,
    "mild_divergence": 0,
    "medium_opportunity": 0,
    "high_opportunity": 0,
    "not_evaluable": 0
  },
  "warnings": []
}
```

## Frontend integration rules

1. Load `/api/discovery/options` before rendering preset and capability controls.
2. Treat `snapshot_id` as required state for every search; do not submit a live ticker list as a substitute.
3. Render `limitations`, `exclusions`, and `warnings` alongside results; an empty feed is a valid outcome.
4. Format ratios for display only: `0.15` becomes `15%`; retain the original number when sending filters.
5. Do not label `research_fit`, percentile, or discrepancy as probability, expected return, or recommendation.
6. Keep `display_mode` presentation-only.

## Compatibility policy

The `ResearchMandate` version is `v1`. Additive response fields are compatible. Renaming/removing fields, changing enum values, units, filter semantics, ranking order, or fixed preset weights requires a new contract version and corresponding frontend update. The generated `/openapi.json` must be checked after any endpoint or Pydantic model change.
