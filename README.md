# SiteSage — Royal Edition

A prototype, agentic site-selection system that evaluates retail locations (initially coffee shops in Shanghai) with explainable, data-driven insights. It runs a staged analysis pipeline, saves step-by-step reports, and presents a modern golden/royal-styled frontend for exploration.

- Agents (LLM + tools where applicable)
  1) Understanding: parse prompt, geocode, static map
  2) Customer: population and demographics
  3) Traffic: transit/parking accessibility
  4) Competition: competitor density/proximity
  5) Weighting: derive weights for each area and compute the final score
  6) Final Report: no tools; produce a polished, executive-friendly summary with a recommendation

- Tools
  - AMap wrapper (geocoding, nearby POIs, distance matrix) via `tools/map_rt.py`
  - Population stats via `tools/demographics_rt.py` (WorldPop rasters)
  - Optional lightweight web search via `ddgs`
  - Static map preview via Leaflet (frontend)

---

## Table of Contents

- [Demo](#demo)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Setup](#setup)
- [Run the Frontend](#run-the-frontend)
- [Run Backend Demo Only](#run-backend-demo-only)
- [API Usage](#api-usage)
- [Result Schema](#result-schema)
- [Project Structure](#project-structure)
- [Artifacts and Logs](#artifacts-and-logs)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Extending](#extending)
- [Credits](#credits)

---

## Demo

1) Start the frontend server
```bash
python -c "import sitesage_frontend as f; f.main()"
```

2) Open the app in a browser
- http://127.0.0.1:8000

3) In the left panel:
- Select language (EN/中文)
- Enter a prompt (example below)
- Click “Run Analysis”

Example prompt:
```
Open a boutique coffee shop with a cozy vibe targeting young professionals and students.
Strong morning traffic is desired. The location is near 南京东路300号, 黄浦区, 上海.
```

4) Explore results
- Right pane shows an interactive map first.
- The “Artifacts” list (bottom-left) will populate with step-wise markdown reports and the “Final Report.” Click to view in the right pane.

---

## Architecture

- Orchestrated agentic pipeline (LLM + tools):
  - UnderstandingAgent → tool_get_place_info, tool_build_static_map
  - CustomerAgent → tool_get_population_stats
  - TrafficAgent → tool_get_nearby_places, tool_get_distances
  - CompetitionAgent → tool_get_nearby_places, tool_get_distances
  - WeightingAgent → no tools; JSON weights
  - FinalReportAgent → no tools; full markdown report

- Data sources:
  - AMap (geocoding, POIs, distance)
  - WorldPop rasters (population/age composition)
  - OpenStreetMap tiles (frontend map)

- Design highlights:
  - Iterative tool-calling within each agent (LLM can adjust parameters like radius/pages)
  - Robust tool wrappers (accept flexible parameter names: types vs descriptive_types, pages vs num_pages, lat/lng vs lon)
  - Step artifacts saved as markdown under save/<session_id>/

---

## Requirements

- Python 3.9+ (tested on 3.12)
- Packages:
  - railtracks
  - ddgs
  - fastapi
  - uvicorn
- API keys and provider configs set up for:
  - OpenAI (for railtracks LLM): `OPENAI_API_KEY`
  - AMap (if your `tools/map_rt.py` needs AMap keys)
  - WorldPop rasters preloaded/accessible by your `tools.demographics` implementation

Install dependencies:
```bash
pip install railtracks ddgs fastapi uvicorn
```

Environment variables:
```bash
# Linux/macOS
export OPENAI_API_KEY="your-openai-key"

# Windows PowerShell
$env:OPENAI_API_KEY="your-openai-key"
```

---

## Setup

Place files as follows (example):
```
project/
├─ sitesage_backend.py
├─ sitesage_frontend.py
├─ frontend/
│  └─ index.html
└─ tools/
   ├─ map_rt.py                # wraps your MapTool (AMap-based)
   └─ demographics_rt.py       # wraps your DemographicsTool (WorldPop)
```

Ensure `tools/map_rt.py` and `tools/demographics_rt.py` import correctly and are configured for your environment.

---

## Run the Frontend

Start the server:
```bash
python -c "import sitesage_frontend as f; f.main()"
```

Then open:
- http://127.0.0.1:8000

The server prints clear console logs:
- System start
- GET /
- POST /api/run -> request in
- POST /api/run -> returned (final score and elapsed)

---

## Run Backend Demo Only

You can run the backend demo without the frontend:
```bash
python -c "import sitesage_backend as b; b.main()"
```

It will:
- Execute a demo prompt (in Chinese by default)
- Save artifacts under save/demo_session/
- Print a console summary (final score, weights, report path)

---

## API Usage

The frontend uses a simple REST endpoint.

- POST /api/run
  - Body (JSON):
    - session_id (optional): string. If omitted, server generates one from timestamp.
    - prompt: string (required)
    - language: "en" | "zh" (default: "en")
  - Response: a JSON document described in [Result Schema](#result-schema)

Example cURL:
```bash
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
        "prompt": "Open a boutique coffee shop with a cozy vibe targeting young professionals and students. Strong morning traffic is desired. The location is near 南京东路300号, 黄浦区, 上海.",
        "language": "zh"
      }'
```

---

## Result Schema

The backend returns a dict with the following keys:
- session_id (str)
- input (dict)
  - prompt (str)
  - language (str)
- store_info (dict)
  - store_type (str)
  - business_description (str)
  - service_mode (str)
  - target_customers (List[str])
  - price_level (str)
  - time_window (str)
  - location_query (str)
- place (dict)
  - Provider place payload (opaque)
  - Normalized coordinates included when available: lat (float), lng (float), lon (float)
- features (dict)
  - customer (dict): {radius_m: float, population_total: float|None, age_buckets: object|None, notes: str|None}
  - traffic (dict): {nearby_counts: object, distances: object, nearest_transit: object, notes: str|None}
  - competition (dict): {competitor_counts: object, nearest_competitor: object, notes: str|None}
- scores (dict)
  - customer/traffic/competition: {"score": float, "justification": str}
- weights (dict)
  - customer (float)
  - traffic (float)
  - competition (float)
  - justification (str)
- final_score (float)
- final_report (dict)
  - title (str)
  - recommendation (str)
  - highlights (List[str])
  - report_path (str) → the saved markdown
- assets (dict)
  - reports (dict): step_name → path to saved markdown file
  - map_image_url (str) (fallback; the frontend uses Leaflet live map)
- errors (List[str])
- timestamps (dict): {started_at: str, ended_at: str}

All step-wise reports (including the Final Report) are saved to `save/<session_id>/`.

---

## Project Structure

Key files:
- `sitesage_backend.py`: Agentic pipeline and tools. Produces all analysis and writes reports.
- `sitesage_frontend.py`: FastAPI server serving the UI and endpoint `/api/run`.
- `frontend/index.html`: Golden/royal-styled SPA. Left panel for input/config and artifacts; right panel is a live map or markdown viewer.
- `tools/map_rt.py`: Thin wrapper over your MapTool (AMap).
- `tools/demographics_rt.py`: Thin wrapper over your DemographicsTool (WorldPop).

Generated:
- `save/<session_id>/`
  - `01_understanding.md` … `05_weighting.md`
  - `06_final_report.md` ← the final executive report
  - (other files or logs as your tools may create)

---

## Artifacts and Logs

- Artifacts: markdown files under `save/<session_id>/` and accessible via `http://127.0.0.1:8000/save/<session_id>/...`
- Logs:
  - Frontend prints high-signal logs to the terminal (system start, request in, returned).
  - Tool-specific logs appear in the terminal depending on your environment.

---

## Troubleshooting

- ERROR “asyncio.run() cannot be called from a running event loop”
  - Fixed. The frontend awaits `run_sitesage_session_async` instead of calling the sync wrapper.

- Map not rendering / DNS issues (static image)
  - The UI now uses Leaflet live map with OSM tiles, including a fallback tile provider.

- AMap/coordinates mismatch (lon vs lng)
  - Tools normalize coordinates and include both `lng` and `lon`. If your provider response schema differs, check `save/<session_id>/` artifacts and adjust the wrappers.

- Missing provider data or API keys
  - Ensure AMap and demographic tools are configured and reachable. Set `OPENAI_API_KEY` for LLM.

- Large artifacts not showing in UI
  - The UI renders markdown using Marked. Verify the links under “Artifacts” point to `/save/...`.

---

## Limitations

- Prototype scope:
  - Geography: Shanghai, China
  - Domain: Coffee shops
  - Focus: Customer traffic; costs not modeled
- Open data reliance and potential drift (internet/API changes)
- LLM variability; no long-term caching implemented

---

## Extending

- Add more categories:
  - Expand `suggested_types`/`descriptive_types` for Traffic/Competition agents.
- More geographies:
  - Update your `tools/` to support different providers or coordinate systems.
- Extra steps:
  - Add agents for pricing, real-estate availability, or custom KPIs.
- UI:
  - Add a “Preview Final Report” auto-open behavior after analysis.
  - Add export (PDF) with a server-side renderer.

---

## Credits

- Maps: Leaflet + OpenStreetMap tiles
- Markdown rendering: Marked
- LLM orchestration: railtracks
- Web search: ddgs (DuckDuckGo Search)
- Data sources: AMap LBS, WorldPop

---

## License

Prototype code for academic/project purposes. Ensure you comply with the terms of the external APIs and data sources you use.
