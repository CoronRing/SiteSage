# SiteSage — System Design Document (Royal Edition)

Version: 1.0  
Last updated: 2025-11-15  
Audience: Developers, integrators, and future maintainers

This document specifies the architecture, components, data contracts, and behavior of the SiteSage prototype. It is intended to serve as a definitive reference for future development, maintenance, and extensibility.

---

## 1. Overview

SiteSage is a staged, agentic site-selection system that evaluates user-specified locations for a specific retail concept (initially: coffee shops in Shanghai). It synthesizes structured context via map tools and demographics, then produces both quantitative scores and a qualitative final report. The system follows a modular pipeline of agents (LLM + tools as applicable), each responsible for a domain aspect.

Core design principles:
- Predictable orchestration, agentic steps with bounded tool calls.
- Clear return schema for frontend consumption.
- Reproducibility via saved, human-readable markdown artifacts per step.
- Robust tool wrappers that normalize parameters and provider idiosyncrasies.

---

## 2. Architecture

High-level components:
- Backend (Python):
  - Orchestrated 6-step agentic pipeline using railtracks with function tools.
  - Tool wrappers for maps (AMap) and demographics (WorldPop).
  - Session artifact writer and standardized result schema.

- Frontend (FastAPI + HTML/JS):
  - Single-page UI in a golden/royal theme.
  - Left panel: config and input; artifact list (files, map button).
  - Right panel: interactive map viewer or markdown viewer.
  - REST endpoint /api/run to trigger the full pipeline and retrieve results.

Data flow summary:
1) FE POST /api/run → BE agentic pipeline executes → writes markdown per step → returns JSON with paths and metrics.
2) FE lists artifacts and displays map initially; clicking an artifact loads and renders the markdown on the right.

---

## 3. Backend Design

File: `sitesage_backend.py`

### 3.1. External Dependencies and Tools

- railtracks: LLM orchestration framework.
- ddgs: Lightweight web search (used as an optional tool; currently not integral to final scoring).
- tools/map_rt.py: Wrapper for MapTool (AMap LBS APIs).
- tools/demographics_rt.py: Wrapper for DemographicsTool (WorldPop rasters).
- OpenAI LLMs via railtracks.llm.OpenAILLM ("gpt-4o" in this prototype).

Environment requirements:
- `OPENAI_API_KEY` must be set to run LLM agents.
- Any AMap or other provider keys/config must be available to `tools/map_rt.py`.
- Demographic resources configured for `tools/demographics_rt.py`.

### 3.2. Result Schema (Authoritative)

The backend returns a dictionary with the following keys:

- session_id (str)
- input (dict):
  - prompt (str)
  - language (str)
- store_info (dict):
  - store_type (str)
  - business_description (str)
  - service_mode (str)
  - target_customers (List[str])
  - price_level (str)
  - time_window (str)
  - location_query (str)
- place (dict): Provider payload (opaque); fields are provider-dependent; normalized keys include lat (float), lng (float), lon (float) when available.
- features (dict):
  - customer (dict): {radius_m: float, population_total: float|None, age_buckets: object|None, notes: str|None}
  - traffic (dict): {nearby_counts: object, distances: object, nearest_transit: object, notes: str|None}
  - competition (dict): {competitor_counts: object, nearest_competitor: object, notes: str|None}
- scores (dict):
  - customer/traffic/competition: {"score": float, "justification": str}
- weights (dict):
  - customer (float), traffic (float), competition (float), justification (str)
- final_score (float)
- final_report (dict):
  - title (str)
  - recommendation (str)
  - highlights (List[str])
  - report_path (str) → saved markdown path
- assets (dict):
  - reports (dict): step_name → path to saved markdown file
  - map_image_url (str): static map URL (fallback; FE uses live map)
- errors (List[str])
- timestamps (dict): {"started_at": str, "ended_at": str} (ISO-8601 with timezone)

### 3.3. Orchestration Pipeline

Function: `run_sitesage_session_async(session_id: str, prompt: str, *, language: str = "en") -> Dict[str, Any]`

- Ensures the session directory `save/<session_id>/`.
- Runs 6 agents in sequence:
  1) UnderstandingAgent (tools: get_place_info, build_static_map)
  2) CustomerAgent (tools: get_population_stats)
  3) TrafficAgent (tools: get_nearby_places, get_distances)
  4) CompetitionAgent (tools: get_nearby_places, get_distances)
  5) WeightingAgent (no tools)
  6) FinalReportAgent (no tools)
- Writes a markdown report per step and aggregates results.
- Returns fully structured output plus artifact paths.

Helper wrapper: `run_sitesage_session(...)`  
- Synchronous wrapper around the async pipeline (CLI convenience).
- Note: In server contexts (e.g., FastAPI), call the async function directly to avoid nested event loops.

### 3.4. Agents

Each agent is created by a `make_*_agent()` function that returns a railtracks agent node with:
- A system message explaining the task.
- Tool nodes (if applicable).
- An LLM model (OpenAILLM("gpt-4o")).
- Optional `max_tool_calls` cap to prevent runaway loops.

1) UnderstandingAgent
- Purpose: Extract structured `store_info`, geocode `place`, and produce a static map URL.
- Tools:
  - `tool_get_place_info(address|query, language=None, extra_params=None) -> dict`
  - `tool_build_static_map(lat, lng, zoom=16, width=600, height=400) -> str`
- Output JSON fields: store_info, place, map_image_url, report_md.

2) CustomerAgent
- Purpose: Estimate population and demographics within a radius; iterate across radii if needed.
- Tool:
  - `tool_get_population_stats(location|lat/lng, radius_m=500.0, coord_ref="GCJ-02") -> dict`
- Output JSON fields: features, score, justification, report_md.

3) TrafficAgent
- Purpose: Evaluate access and transit proximity, experimenting with radius and pagination.
- Tools:
  - `tool_get_nearby_places(origin|location, descriptive_types|types, radius, rank="DISTANCE", include_details=False, num_pages|pages=2) -> list`
  - `tool_get_distances(origin|location, destinations, mode="walk", units="metric") -> list`
- Output JSON fields: features, score, justification, report_md.

4) CompetitionAgent
- Purpose: Evaluate competitive landscape (density and nearest competitor).
- Tools: same as TrafficAgent.
- Output JSON fields: features, score, justification, report_md.

5) WeightingAgent
- Purpose: Produce normalized weights for customer, traffic, competition; include justification.
- Tools: none.
- Output JSON fields: weights, justification, report_md.

6) FinalReportAgent
- Purpose: Produce a polished, executive-friendly markdown report based on all previous step outputs.
- Tools: none.
- Output JSON fields: title, recommendation, highlights, report_md.

### 3.5. Tool Wrappers (Function Nodes)

All tools accept flexible parameter names to be robust to LLM variability and provider differences.

- `tool_get_place_info(address: Optional[str] = None, *, query: Optional[str] = None, language: Optional[str] = None, extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`
  - Wraps `tools.map_rt.getPlaceInfo`.
  - Normalizes to include `lat`, `lng`, and `lon` keys when possible.

- `tool_get_nearby_places(origin: Optional[Dict[str, Any]] = None, *, location: Optional[Dict[str, Any]] = None, descriptive_types: Optional[Sequence[str]] = None, types: Optional[Sequence[str]] = None, radius: int = 500, rank: str = "DISTANCE", include_details: bool = False, num_pages: int = 2, pages: Optional[int] = None) -> List[Dict[str, Any]]`
  - Wraps `tools.map_rt.getNearbyPlaces`.
  - Accepts either `descriptive_types` or `types`.
  - Accepts `num_pages` or `pages`.
  - Normalizes origin for `lat`,`lng`,`lon`.

- `tool_get_distances(origin: Optional[Dict[str, Any]] = None, *, location: Optional[Dict[str, Any]] = None, destinations: Sequence[Dict[str, Any]] = (), mode: str = "walk", units: str = "metric") -> List[Dict[str, Any]]`
  - Wraps `tools.map_rt.getDistances`.
  - Normalizes origin/destinations to include both `lng` and `lon`.

- `tool_get_population_stats(location: Optional[Dict[str, Any]] = None, *, lat: Optional[float] = None, lng: Optional[float] = None, lon: Optional[float] = None, radius_m: float = 500.0, coord_ref: str = "GCJ-02") -> Dict[str, Any]`
  - Wraps `tools.demographics_rt.getPopulationStats`.
  - Can accept explicit `lat`,`lng` or a `location` dict.
  - Normalizes output keys to `population_total`, `age_buckets`, and `notes`.

- `tool_build_static_map(lat: Optional[float] = None, lng: Optional[float] = None, *, origin: Optional[Dict[str, Any]] = None, location: Optional[Dict[str, Any]] = None, zoom: int = 16, width: int = 600, height: int = 400) -> str`
  - Builds a static map URL using OpenStreetMap. Frontend uses live Leaflet map, but this is retained for consistency.

- `tool_web_search(query: str, max_results: int = 5, region: str = "wt-wt") -> List[Dict[str, str]]`
  - Optional qualitative context search.

### 3.6. Backend Utilities

- `ensure_session_dir(session_id: str) -> str`
  - Creates `save/<session_id>/` if missing and returns absolute path.

- `write_markdown(session_dir: str, name: str, content: str) -> str`
  - Writes `name.md` under `session_dir`. Returns absolute path.

- `parse_json_from_text(text: str) -> Any`
  - Robustly extracts JSON from LLM responses (handles fenced code blocks ```json ... ``` and substring JSON).

- `_as_float(v: Any) -> Optional[float]`
  - Safe float coercion helper.

- `extract_lat_lng(obj: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float]]`
  - Searches for lat/lng keys across typical nested shapes; returns `(lat, lng)`.

- `normalize_geo(d: Mapping[str, Any]) -> Dict[str, Any]`
  - Ensures dict includes both `lng` and `lon` from whichever is present.

- `normalize_types(val: Any) -> List[str]`
  - Coerces strings, lists, and ignores booleans into a clean `List[str]`.

- `osm_static_map_url(lat: float, lng: float, zoom: int, width: int, height: int) -> str`
  - Prototype-only URL builder.

---

## 4. Frontend Design

File: `sitesage_frontend.py` and `frontend/index.html`

### 4.1. Server (FastAPI)

Functions:
- `_configure_console_logging() -> None`
  - Console logging at INFO level for high-signal messages (startup, request in, returned).
  - Tames noisy loggers.

- `create_app() -> FastAPI`
  - Mounts:
    - `/` serves `frontend/index.html`
    - `/api/run` POST endpoint
    - `/save` serves artifacts (reports/logs)
    - `/frontend` serves static assets if needed
  - Handlers:
    - `@app.on_event("startup")` logs system start.
    - `GET /`: returns the SPA HTML (errors if not found).
    - `POST /api/run`: Accepts JSON `{session_id?, prompt, language}`, awaits `backend.run_sitesage_session_async` and returns the result JSON. If `session_id` omitted, derived from current time.
    - `GET /healthz`: returns `ok`.

- `main() -> None`
  - Runs Uvicorn on `127.0.0.1:8000`.

Important design choice:
- Avoids calling `asyncio.run()` inside FastAPI endpoints; instead awaits `run_sitesage_session_async` to prevent nested event loop errors.

### 4.2. Single-Page UI (HTML + JS)

File: `frontend/index.html`

Layout:
- Left (controls and artifacts):
  - Language selector, prompt textarea.
  - "Run Analysis" button and status/errors area.
  - “Artifacts” list: contains a Map button and links to generated markdown files (including Final Report).
  - “Summary” chips: final score and weights.
- Right (viewer):
  - Shows interactive map first (Leaflet).
  - When an artifact is clicked, the right viewer switches to a markdown document rendered by Marked.

Key JavaScript functions:
- `defaultSessionId() -> string`:
  - Generates an ID based on current time; used if frontend supplies `session_id`.

- `savePathToUrl(path: string) -> string|null`:
  - Converts absolute file paths returned by backend to `/save/<session_id>/...` URLs.

- Map functions:
  - `initMap(lat=31.2304, lng=121.4737, zoom=14)`:
    - Creates a Leaflet map instance; defaults to Shanghai center if no coordinates available.
  - `addTileLayerWithFallback()`:
    - Adds a tile layer with fallback to a secondary OSM provider if the first fails.
  - `showMap()`:
    - Switches viewer to map mode.
  - `updateMapFromResult(res)`:
    - Extracts lat/lng from `res.place` and re-centers the map and marker.

- Document rendering:
  - `showMarkdownFromUrl(url: string, title: string)`:
    - Fetches and renders markdown in the right viewer.

- Artifact list and summary:
  - `renderArtifactsAndSummary(res)`:
    - Populates “Artifacts” with file links (sorted by step).
    - Displays final score and weights as chips.

- Orchestration:
  - `runAnalysis()`:
    - Gathers input, creates `session_id`, POSTs to `/api/run`, then calls `updateMapFromResult` and `renderArtifactsAndSummary`.

UX behavior:
- After a successful run, the map updates to the geocoded location.
- Users can toggle back to the map via the “Map” button.
- Clicking a file loads it in the doc viewer.

---

## 5. File Naming and Storage

Artifacts are saved per session in `save/<session_id>/` with the following expected files:
- `01_understanding.md`
- `02_customer.md`
- `03_traffic.md`
- `04_competition.md`
- `05_weighting.md`
- `06_final_report.md` (Final report)
- Optionally, logs or raw dumps if you add them (e.g., `00_place_raw.json` in earlier versions)

Frontend converts returned artifact paths to `/save/...` URLs for inline viewing.

---

## 6. Error Handling and Logging

- Backend:
  - Internal per-function try/except only where appropriate; fast-fail elsewhere.
  - Agent steps are expected to produce valid JSON via `parse_json_from_text`. If parsing fails, errors bubble up to the frontend (HTTP 500).
  - Tool wrappers raise `ValueError` for invalid inputs (e.g., missing lat/lng), which the LLM can correct through iterative calls.

- Frontend:
  - Console logs at INFO level: system start, GET /, POST /api/run request in, POST /api/run returned summary.
  - Returns HTTP 400 for invalid input and HTTP 500 for backend failures with a clear message “Backend failure: …”.

- Known transient issues and stability:
  - DNS/Tile server failures: Leaflet tile layer fallback.
  - AMap limits: when POI counts appear capped (e.g., 25 per page), agents may increase pages or radii.

---

## 7. Security and Privacy

- This is a prototype; no authentication or authorization is implemented.
- Do not expose the server to the public internet without adding auth controls.
- Do not log sensitive data in production; currently, the system logs prompts and session IDs.

---

## 8. Performance Considerations

- railtracks agent calls are sequential; total latency is the sum of LLM turn time and tool calls.
- Tune agent caps:
  - `max_tool_calls` per agent to control cost/time.
- Reduce payload sizes:
  - Only return necessary fields in tools and features.
- Caching (future):
  - Cache geocoding results by address; cache POI searches per origin/radius/categories.

---

## 9. Extensibility

- Add domains:
  - Define new agents (e.g., Real Estate, Pricing).
  - Create new tool wrappers (e.g., different map providers).
- Add geographies:
  - Update `tools.map_rt` and type projection mappings for other cities/countries.
- Add outputs:
  - Add agent to produce PDF (e.g., using a server-side renderer) or JSON-only APIs for other clients.
- Parameterization:
  - Allow frontend to specify analysis radii, categories, or page limits.

---

## 10. Testing Strategy (Recommended)

- Unit tests:
  - Tool wrappers: parameter normalization; origin/destination handling.
  - Utilities: `parse_json_from_text`, `extract_lat_lng`, `normalize_geo`.
- Integration tests:
  - Mocked `tools.map_rt` and `tools.demographics_rt` to validate the pipeline.
  - Verify artifact creation and result schema.
- End-to-end:
  - Start the server; run predefined prompts; verify saved files and UI rendering via Playwright or Cypress.

---

## 11. Deployment

- Local development:
  - `python -c "import sitesage_frontend as f; f.main()"`
- Containerization:
  - A single image containing backend and frontend server.
  - Environment variables provided at runtime.
- Production notes:
  - Add reverse proxy (Nginx) with TLS.
  - Implement authentication (e.g., OAuth2) for `/api/run` and `/save`.
  - Rate limits and request size limits.

---

## 12. Function Catalog (Backend)

This section enumerates key functions and their responsibilities.

Utilities:
- `ensure_session_dir(session_id: str) -> str`
  - Ensure the session directory exists; return absolute path.

- `write_markdown(session_dir: str, name: str, content: str) -> str`
  - Write a markdown file and return its path.

- `parse_json_from_text(text: str) -> Any`
  - Extract well-formed JSON from an LLM response even if surrounded by fences.

- `_as_float(v: Any) -> Optional[float]`
  - Safe numeric conversion.

- `extract_lat_lng(obj: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float]]`
  - Deep search for latitude and longitude.

- `normalize_geo(d: Mapping[str, Any]) -> Dict[str, Any]`
  - Standardize coordinate keys; add `lng` and `lon`.

- `normalize_types(val: Any) -> List[str]`
  - Clean up LLM-provided type categories into a list of strings.

- `osm_static_map_url(lat: float, lng: float, zoom: int, width: int, height: int) -> str`
  - Build a static map URL for fallback use.

Tools:
- `tool_get_place_info(address|query, language=None, extra_params=None) -> dict`
  - Geocode; normalize lat/lng/lon.

- `tool_get_nearby_places(origin|location, descriptive_types|types, radius, rank="DISTANCE", include_details=False, num_pages|pages=2) -> list`
  - Fetch POIs.

- `tool_get_distances(origin|location, destinations, mode="walk", units="metric") -> list`
  - Distance matrix.

- `tool_get_population_stats(location|lat/lng, radius_m=500.0, coord_ref="GCJ-02") -> dict`
  - Demographic stats near a point.

- `tool_build_static_map(lat, lng, zoom=16, width=600, height=400) -> str`
  - Build OSM static map URL.

- `tool_web_search(query, max_results=5, region="wt-wt") -> list`
  - Optional contextual web search.

Agent constructors:
- `make_understanding_agent() -> Any`
- `make_customer_agent() -> Any`
- `make_traffic_agent() -> Any`
- `make_competition_agent() -> Any`
- `make_weighting_agent() -> Any`
- `make_final_report_agent() -> Any`

Orchestration:
- `run_sitesage_session_async(session_id: str, prompt: str, *, language: str = "en") -> Dict[str, Any]`
  - Execute full pipeline; generate reports; return result.

- `run_sitesage_session(session_id: str, prompt: str, *, language: str = "en") -> Dict[str, Any]`
  - Synchronous convenience wrapper (not for async server contexts).

---

## 13. Function Catalog (Frontend)

Server: `sitesage_frontend.py`
- `_configure_console_logging() -> None`
  - INFO logs; minimal and clear.
- `create_app() -> FastAPI`
  - Register endpoints and static mounts.
- `main() -> None`
  - Start Uvicorn.

Endpoints:
- `GET /`
  - Serves `frontend/index.html`.
- `POST /api/run`
  - Request: `{session_id?, prompt, language}`
  - Behavior: awaits `backend.run_sitesage_session_async(...)` and returns JSON result.
- `GET /healthz`
  - Liveness check.

SPA: `frontend/index.html` (JS inline)
- `defaultSessionId()`
- `savePathToUrl(path)`
- Map:
  - `initMap(lat, lng, zoom)`
  - `addTileLayerWithFallback()`
  - `showMap()`
  - `updateMapFromResult(res)`
- Docs:
  - `showMarkdownFromUrl(url, title)`
- Rendering:
  - `renderArtifactsAndSummary(res)`
- Orchestration:
  - `runAnalysis()`

---

## 14. Known Issues and Future Work

- Fine-grained provider errors:
  - Surface granular error messages from AMap/WorldPop tools in a user-friendly way.
- Scalability:
  - Introduce async tool calls where possible; parallelize independent queries (e.g., different radii).
- Advanced UI features:
  - Add a viewer toolbar (search, TOC, export PDF).
  - Auto-open the Final Report upon completion.
- Multi-language final report:
  - Language-specific formatting and style.

---

## 15. Appendix: Sequence Overview

Textual sequence (for a typical request):

1) FE → BE: POST /api/run {prompt, language, session_id?}
2) BE: ensure save/session; UnderstandingAgent:
   - Calls `tool_get_place_info(address=…)`
   - Calls `tool_build_static_map(lat, lng)`
   - Saves 01_understanding.md
3) CustomerAgent:
   - Calls `tool_get_population_stats(location, radius_m=… [tries multiple])`
   - Saves 02_customer.md
4) TrafficAgent:
   - Calls `tool_get_nearby_places(origin, types=[…], radius=…, pages=…)` (iteratively)
   - Calls `tool_get_distances(origin, destinations)`
   - Saves 03_traffic.md
5) CompetitionAgent:
   - Same tool set as TrafficAgent; different types (coffee_shop, cafe)
   - Saves 04_competition.md
6) WeightingAgent:
   - Produces weights and justification
   - Saves 05_weighting.md
7) FinalReportAgent:
   - Produces a polished markdown report
   - Saves 06_final_report.md
8) BE → FE: returns result JSON including artifacts and final score
9) FE:
   - Updates map and artifact list
   - Renders markdown on click

---

## 16. Glossary

- Agent: An LLM node configured with tools and prompt to perform a discrete analytical task.
- Tool: A function node that performs a deterministic operation (e.g., geocode, POI search).
- Artifact: A saved markdown report per step to facilitate debugging, auditing, and user-friendly presentation.
- Session: A single evaluation run with a unique session_id (usually time-based).

---

End of document.