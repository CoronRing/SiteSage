# SiteSage — System Design Document (Royal Edition)

Version: 1.0  
Last updated: 2025-11-15  
Audience: Developers, integrators, and future maintainers

This document specifies the architecture, components, data contracts, and behavior of the SiteSage prototype. It is intended to serve as a definitive reference for future development, maintenance, and extensibility.

---

## 1. Overview

SiteSage is a staged, agentic site-sele## 11. Testing Strategy (Re## 13. Function Catalog (Backend)ommended)tion system that evaluat## 14. Function Catalog (Frontend)s ## 15. Known I## 16. Appendix: Sequence Overviewsues and Futu## 17. Glossary

- **Agent**: An LLM node configured with tools and prompt to perform a discrete analytical task.
- **Tool**: A function node that performs a deterministic operation (e.g., geocode, POI search).
- **Artifact**: A saved markdown report per step to facilitate debugging, auditing, and user-friendly presentation.
- **Session**: A single evaluation run with a unique session_id (usually time-based).
- **Sequential Flow**: Architecture pattern where each agent receives outputs from previous agents, enabling contextual awareness and synthesis.
- **Rubric**: Standardized scoring criteria document (markdown) defining evaluation standards for each analysis domain or weighting guidelines.
- **Evaluation Agent**: Specialized agent that scores analysis reports objectively using evaluation rubrics, separate from analysis agents.
- **Weighting Agent**: Specialized agent that determines domain importance using weighting rubric, based on business context (NOT analysis quality).
- **Logical Parallelism**: Weighting and Evaluation are conceptually independent operations executed sequentially for simplicity. Neither depends on the other's output.
- **Weighted Score**: Final score calculated by multiplying each domain score by its weight and summing: `final_score = (customer_score × w_customer) + (traffic_score × w_traffic) + (competition_score × w_competition)`.kser-specified locations for a specific retail concept (initially: coffee shops in Shanghai). It synthesizes structured context via map tools and demographics, then produces both quantitative scores and a qualitative final report. The system follows a modular pipeline of agents (LLM + tools as applicable), each responsible for a domain aspect.

Core design principles:
- Predictable orchestration, agentic steps with bounded tool calls.
- Clear return schema for frontend consumption.
- Reproducibility via saved, human-readable markdown artifacts per step.
- Robust tool wrappers that normalize parameters and provider idiosyncrasies.

---

## 2. Architecture

High-level components:
- Backend (Python):
  - Orchestrated 7-step agentic pipeline using railtracks with function tools.
  - Sequential data flow: each analysis agent receives reports from previous agents.
  - Tool wrappers for maps (AMap) and demographics (WorldPop).
  - Rubric-based evaluation system with separate scoring agent.
  - Session artifact writer and standardized result schema.

- Frontend (FastAPI + HTML/JS):
  - Single-page UI in a golden/royal theme.
  - Left panel: config and input; artifact list (files, map button).
  - Right panel: interactive map viewer or markdown viewer.
  - REST endpoint /api/run to trigger the full pipeline and retrieve results.

Data flow summary:
1) FE POST /api/run → BE agentic pipeline executes in sequence → each agent receives prior reports → writes markdown per step → evaluation agent scores all analyses using rubrics → returns JSON with paths, scores, and metrics.
2) FE lists artifacts and displays map initially; clicking an artifact loads and renders the markdown on the right.

Sequential pipeline flow:
- Understanding → Customer → Traffic (receives customer report) → Competition (receives customer + traffic reports) → Weighting → Evaluation (scores using rubrics) → Final Report (synthesizes with scores)

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
  - customer (float): score 0-10 from evaluation agent
  - traffic (float): score 0-10 from evaluation agent
  - competition (float): score 0-10 from evaluation agent
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
- Runs 7 agents in sequence with sequential data flow:
  1) UnderstandingAgent (tools: get_place_info, build_static_map)
  2) CustomerAgent (tools: get_population_stats) → produces markdown report
  3) TrafficAgent (tools: get_nearby_places, get_distances) → receives customer report
  4) CompetitionAgent (tools: get_nearby_places, get_distances) → receives customer + traffic reports
  5) WeightingAgent (no tools) → determines domain weights
  6) EvaluationAgent (no tools) → scores all three analyses using rubrics from `rubrics/` directory
  7) FinalReportAgent (no tools) → synthesizes with scores
- Each analysis agent (2-4) returns natural language markdown reports, not self-scored JSON.
- Evaluation agent loads rubric files and objectively scores each domain (0-10 scale).
- Writes a markdown report per step and aggregates results.
- Returns fully structured output plus artifact paths and evaluation scores.

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
- Output: Natural language markdown report analyzing customer potential (no self-scoring).
- Sequential flow: Receives store_info and place only (first analysis agent).

3) TrafficAgent
- Purpose: Evaluate access and transit proximity, experimenting with radius and pagination.
- Tools:
  - `tool_get_nearby_places(origin|location, descriptive_types|types, radius, rank="DISTANCE", include_details=False, num_pages|pages=2) -> list`
  - `tool_get_distances(origin|location, destinations, mode="walk", units="metric") -> list`
- Output: Natural language markdown report analyzing traffic and accessibility (no self-scoring).
- Sequential flow: Receives customer report and considers customer demographics when evaluating accessibility.

4) CompetitionAgent
- Purpose: Evaluate competitive landscape (density and nearest competitor).
- Tools: same as TrafficAgent.
- Output: Natural language markdown report analyzing competition (no self-scoring).
- Sequential flow: Receives both customer and traffic reports; synthesizes insights about whether customer base can support competitors given accessibility patterns.

5) WeightingAgent
- Purpose: Determine normalized weights for customer, traffic, competition based on business context.
- Tools: none (reads weighting rubric from `rubrics/weighting_rubric.md`).
- Input: Store information (type, target customers, business model) + weighting rubric.
- Does NOT receive: Analysis reports or evaluation scores (to prevent bias).
- Logic: Weights are business-driven, not quality-driven. A coffee shop should prioritize traffic/accessibility regardless of analysis quality.
- Output JSON fields: weights (must sum to 1.0), justification, store_type, report_md.
- Note: Logically parallel to EvaluationAgent - neither depends on the other's output.

6) EvaluationAgent
- Purpose: Objectively score the three analysis reports using detailed rubrics.
- Tools: none (reads rubric files from `rubrics/` directory).
- Input: Customer, traffic, and competition markdown reports + rubric files.
- Rubrics:
  - `rubrics/customer_rubric.md`: Population metrics (30%), demographics match (25%), behavioral patterns (25%), concept alignment (20%)
  - `rubrics/traffic_rubric.md`: Public transit (35%), pedestrian flow (25%), vehicular access (20%), temporal patterns (20%)
  - `rubrics/competition_rubric.md`: Competitor mapping (30%), differentiation (25%), market gaps (25%), threat assessment (20%)
- Output JSON fields: customer (score + justification), traffic (score + justification), competition (score + justification).
- Each score is 0-10 based on rubric criteria.

7) FinalReportAgent
- Purpose: Produce a polished, executive-friendly markdown report synthesizing all analyses with scores.
- Tools: none.
- Input: All three analysis reports, evaluation scores, weights, and final weighted score.
- Output JSON fields: title, recommendation, highlights, report_md.
- Report includes scores prominently to support data-driven decision making.

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

## 5. Rubric-Based Evaluation System

### 5.1. Purpose

The evaluation system provides objective, consistent scoring of analysis quality using detailed rubrics. This separates analysis from evaluation, ensuring that:
- Analysis agents focus on gathering and presenting insights (no self-scoring bias)
- Evaluation is consistent across sessions using standardized criteria
- Scores are transparent and justifiable to stakeholders

### 5.2. Rubric Files

Located in `rubrics/` directory at project root:

**`customer_rubric.md`** - Customer Analysis Scoring (0-10 scale)
- Population Metrics (30%): Coverage of population data, demographic breakdowns, density calculations
- Demographics Match (25%): Alignment of demographics with target customer profiles
- Behavioral Patterns (25%): Insights about customer behavior, spending patterns, preferences
- Concept Alignment (20%): How well the customer base fits the business concept

**`traffic_rubric.md`** - Traffic & Accessibility Scoring (0-10 scale)
- Public Transit (35%): Transit station proximity, service frequency, accessibility
- Pedestrian Flow (25%): Foot traffic patterns, walkability, pedestrian infrastructure
- Vehicular Access (20%): Parking availability, road access, driving convenience
- Temporal Patterns (20%): Peak hours, day/night patterns, seasonal variations

**`competition_rubric.md`** - Competition Analysis Scoring (0-10 scale)
- Competitor Mapping (30%): Identification and location of competitors, density analysis
- Differentiation Analysis (25%): Assessment of competitive advantages and positioning
- Market Gaps (25%): Identification of underserved segments or opportunities
- Threat Assessment (20%): Evaluation of competitive pressures and market saturation

**`weighting_rubric.md`** - Weighting Determination Guidelines
- Business-context driven framework for determining domain importance
- Store-type specific recommendations (coffee shops, QSR, boutique retail, etc.)
- Weight ranges and justification guidelines
- Ensures weights reflect business priorities, NOT analysis quality
- Independent from evaluation scores to prevent bias

### 5.3. Weighting vs Evaluation: Logical Parallelism

**Key Design Principle:** Weighting and Evaluation are **logically parallel** operations that are **sequentially executed** for implementation simplicity.

**WeightingAgent (Step 5):**
- **Purpose**: Determine relative importance based on **business context**
- **Input**: Store type, business model, target customers, weighting rubric
- **Does NOT receive**: Analysis reports, evaluation scores, quality metrics
- **Output**: Normalized weights (sum to 1.0) with business justification
- **Example**: Coffee shop → Traffic: 0.38 (highest) because commuter access is critical for this business model

**EvaluationAgent (Step 6):**
- **Purpose**: Assess analysis quality based on **rubric criteria**
- **Input**: Analysis reports (customer, traffic, competition) + evaluation rubrics
- **Does NOT receive**: Weights, business priorities, store type preferences
- **Output**: Quality scores (0-10) with justification for each domain
- **Example**: Traffic analysis → 6.0/10 (adequate but missing temporal patterns)

**Why This Separation?**
- **Prevents Bias**: Poor analysis doesn't reduce a critical factor's weight
- **Business Alignment**: Similar stores get similar weights regardless of analyst skill
- **Transparency**: Clear separation of "what matters" vs "how well analyzed"
- **Actionable**: Low score + high weight = improve analysis; high score + low weight = less critical

### 5.4. Evaluation Process

1. **Input**: Three markdown reports (customer, traffic, competition) + three evaluation rubric files
2. **Processing**: EvaluationAgent (LLM) reads each report and its corresponding rubric
3. **Scoring**: Assigns 0-10 score based on rubric criteria, with detailed justification
4. **Output**: JSON with three score objects: `{score: float, justification: string}`
5. **Final Score Calculation**: 
   - Weights from WeightingAgent (Step 5)
   - Scores from EvaluationAgent (Step 6)
   - Formula: `final_score = (customer_score × customer_weight) + (traffic_score × traffic_weight) + (competition_score × competition_weight)`

### 5.5. Score Interpretation

- **9-10**: Exceptional - Comprehensive analysis exceeding all criteria
- **7-8**: Strong - Thorough analysis meeting all major criteria
- **5-6**: Adequate - Covers basics but missing depth or some criteria
- **3-4**: Weak - Significant gaps in analysis or methodology
- **0-2**: Insufficient - Critical deficiencies or lack of substantive analysis

---

## 6. File Naming and Storage

Artifacts are saved per session in `save/<session_id>/` with the following expected files:
- `01_understanding.md` - Extracted store info and geocoded location
- `02_customer.md` - Customer analysis report (markdown)
- `03_traffic.md` - Traffic & accessibility report (markdown)
- `04_competition.md` - Competition analysis report (markdown)
- `05_weighting.md` - Weight determination and justification
- `05_evaluation.md` - Evaluation scores with justifications for each domain
- `07_final_report.md` - Final synthesized report with all scores
- Optionally, logs or raw dumps if you add them (e.g., `00_place_raw.json` in earlier versions)

Frontend converts returned artifact paths to `/save/...` URLs for inline viewing.

---

## 7. Error Handling and Logging

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

## 8. Security and Privacy

- This is a prototype; no authentication or authorization is implemented.
- Do not expose the server to the public internet without adding auth controls.
- Do not log sensitive data in production; currently, the system logs prompts and session IDs.

---

## 9. Performance Considerations

- railtracks agent calls are sequential; total latency is the sum of LLM turn time and tool calls.
- Tune agent caps:
  - `max_tool_calls` per agent to control cost/time.
- Reduce payload sizes:
  - Only return necessary fields in tools and features.
- Caching (future):
  - Cache geocoding results by address; cache POI searches per origin/radius/categories.

---

## 10. Extensibility

- Add domains:
  - Define new agents (e.g., Real Estate, Pricing).
  - Create new tool wrappers (e.g., different map providers).
  - Add corresponding rubric file for new domain evaluation.
  - Update sequential flow to pass new domain's report to subsequent agents.
- Add geographies:
  - Update `tools.map_rt` and type projection mappings for other cities/countries.
- Add outputs:
  - Add agent to produce PDF (e.g., using a server-side renderer) or JSON-only APIs for other clients.
- Parameterization:
  - Allow frontend to specify analysis radii, categories, or page limits.
- Enhance rubrics:
  - Refine rubric criteria based on stakeholder feedback.
  - Add sub-criteria for more granular scoring.
  - Support multiple rubric versions for different business types.

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
- `make_evaluation_agent() -> Any`
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
  - Note: Sequential flow means agents run one after another (not parallel).
  - Consider parallelizing tool calls within each agent where possible.
- Advanced UI features:
  - Add a viewer toolbar (search, TOC, export PDF).
  - Auto-open the Final Report upon completion.
  - Display evaluation scores prominently in UI summary.
- Multi-language final report:
  - Language-specific formatting and style.
- Rubric refinement:
  - Gather user feedback on scoring accuracy and fairness.
  - Add more detailed sub-criteria for edge cases.
  - Consider multiple rubric sets for different business verticals.

---

## 15. Appendix: Sequence Overview

Textual sequence (for a typical request):

1) FE → BE: POST /api/run {prompt, language, session_id?}
2) BE: ensure save/session; UnderstandingAgent:
   - Calls `tool_get_place_info(address=…)`
   - Calls `tool_build_static_map(lat, lng)`
   - Saves 01_understanding.md
3) CustomerAgent:
   - Receives: store_info, place
   - Calls `tool_get_population_stats(location, radius_m=… [tries multiple])`
   - Returns markdown report (no self-scoring)
   - Saves 02_customer.md
4) TrafficAgent:
   - Receives: store_info, place, **customer_report** ← Sequential flow
   - Calls `tool_get_nearby_places(origin, types=[…], radius=…, pages=…)` (iteratively)
   - Calls `tool_get_distances(origin, destinations)`
   - Considers customer demographics when evaluating accessibility
   - Returns markdown report (no self-scoring)
   - Saves 03_traffic.md
5) CompetitionAgent:
   - Receives: store_info, place, **customer_report, traffic_report** ← Sequential flow
   - Same tool set as TrafficAgent; different types (coffee_shop, cafe)
   - Synthesizes customer base and accessibility when evaluating competition
   - Returns markdown report (no self-scoring)
   - Saves 04_competition.md
6) WeightingAgent (logically parallel to Evaluation):
   - Receives: store_info + weighting rubric
   - Determines weights based on business context (NOT analysis quality)
   - Produces normalized weights and justification
   - Saves 05_weighting.md
7) EvaluationAgent (logically parallel to Weighting):
   - Receives: customer_report, traffic_report, competition_report
   - Loads rubric files from `rubrics/` directory
   - Scores each domain objectively (0-10) using rubric criteria
   - Returns JSON with scores and justifications
   - Saves 05_evaluation.md
8) FinalReportAgent:
   - Receives: all reports + evaluation scores + weights + final weighted score
   - Produces polished markdown report with scores prominently displayed
   - Saves 07_final_report.md
9) BE → FE: returns result JSON including artifacts, evaluation scores, and final weighted score
10) FE:
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