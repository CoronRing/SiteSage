# Store Location Selection Agent System — Design Document (MVP)

Status: Draft for collaboration  
Pilot: Electronics retail, Shanghai (China). Globalizable via provider adapters.  
LLM: GPT-4o for synthesis and qualitative analysis.

## 1) Goals and Non-Goals

Goals
- Deliver a modular, agent-based pipeline that evaluates a candidate store location.
- Use free/low-cost APIs (Baidu/AMap/OSM/etc.) and be provider-agnostic.
- Produce a PDF-ready report with key metrics and narrative for current, 1y, 3y, 5y.
- Strongly typed interfaces so agents can be developed independently and swapped.

Non-Goals (MVP)
- No commercial deployment; internal research/demos only.
- No premium mobility or card transaction data integration (future).
- No deep compliance automation; only surface obvious flags.

## 2) System Overview

High-level flow
- Input: Location + store description.
- Data enrichment: Maps, POIs, transit, demographics, web search.
- Parallel analysis: Customer demand and Competitors.
- Accessibility analysis.
- General market/regulatory signals.
- Synthesis: Consolidate into quantitative forecasts + narrative.

Architecture notes
- Provider adapters for region-specific data sources (Baidu/AMap) with swap capability.
- DAG orchestration with caching, retries, provenance.
- LLM used for synthesis and qualitative insights; numeric outputs computed deterministically where possible.

## 3) Agent Graph and Contracts

Common Agent interface (Python-like)
```
class Agent(Protocol):
    def __init__(self, config: AgentConfig, providers: ProviderRegistry, cache: Cache): ...
    def run(self, input_payload: dict, context: ExecutionContext) -> dict: ...
```

Shared types (simplified)
- ExecutionContext: run_id, location_id, timestamps, provenance collector, logger.
- AgentConfig: tunables per agent, timeouts, feature flags.
- ProviderRegistry: access to geocode, place, routing, demographics, and search providers.
- Cache: read-through/write-through cache with TTL and version tags.

DAG (dependencies)
- LocationIntake → LocationAnalysis → [CustomerAnalysis || CompetitorAnalysis] → AccessibilityAnalysis → GeneralAnalysis → SynthesisReport

## 4) Shared Schemas

LocationIntakeRequest
```
{
  "location_id": "string",
  "address": "string",
  "lat": 31.2304,
  "lng": 121.4737,
  "category": "electronics_retail",
  "subcategory": "multi_brand",
  "size_sqm": 250,
  "price_tier": "mid",
  "brand": "Optional<string>",
  "hours": "Optional<string>",
  "notes": "Optional<string>"
}
```

PlaceFeature
```
{
  "provider": "baidu|amap|osm|other",
  "place_id": "string",
  "name": "string",
  "category": "string",
  "subcategory": "string",
  "lat": 31.23,
  "lng": 121.47,
  "rating": 4.3,
  "review_count": 210,
  "price_level": "Optional<int>",
  "open_hours": "Optional<string>",
  "mall_id": "Optional<string>",
  "floor": "Optional<string>",
  "tags": ["electronics", "phone", "repair"],
  "last_seen": "ISO-8601"
}
```

Catchment
```
{
  "mode": "walk|drive|transit",
  "minutes": 5,
  "polygon_geojson": { "type": "Polygon", "coordinates": [...] },
  "population_residential": 12000,
  "population_daytime_proxy": 9000,
  "coverage_score": 0.82,
  "provenance": ["provider:amap:isochrone:2025-10-15"]
}
```

Competitor
```
{
  "place": PlaceFeature,
  "distance_m": 540,
  "transit_time_min": 8,
  "attractiveness_score": 0.67,
  "est_revenue_range": { "low": 2_000_000, "high": 6_000_000, "currency": "CNY" },
  "uncertainty": 0.35,
  "drivers": ["brand_strength", "mall_anchor", "reviews"],
  "provenance": [...]
}
```

AccessibilityScore
```
{
  "transit_distance_m": 110,
  "walk_connectivity_proxy": 0.74,
  "corner_flag": true,
  "frontage_proxy": 0.6,
  "visibility_proxy": 0.7,
  "parking_proxy": 0.5,
  "delivery_access_proxy": 0.8,
  "alignment_score": 0.71,
  "notes": "Near Line 2 exit; mid-block visibility limited by trees",
  "provenance": [...]
}
```

Forecast
```
{
  "period": "current|1y|3y|5y",
  "visits_range": { "low": 25000, "high": 60000 },
  "conversion_rate_range": { "low": 0.05, "high": 0.12 },
  "AOV_range": { "low": 800, "high": 1800, "currency": "CNY" },
  "revenue_range": { "low": 1_000_000, "high": 9_000_000, "currency": "CNY" },
  "confidence": 0.55,
  "assumptions": ["AOV midpoint 1200 CNY", "electronics purchase frequency low"],
  "provenance": [...]
}
```

ReportBundle
```
{
  "key_metrics": { "rev_current": "...", "rev_1y": "...", "rev_3y": "...", "rev_5y": "..." },
  "narrative_text": "string",
  "tables": [{ "title": "Competitors", "rows": [...] }],
  "charts_meta": [{ "type": "bar", "data_key": "forecast_revenue" }],
  "citations": [{ "source": "Baidu Maps", "url": "...", "timestamp": "..." }],
  "data_gaps": ["No mall floor info"],
  "sensitivities": [{ "param": "AOV", "impact": "high" }]
}
```

ProvenanceItem
```
{ "agent": "CompetitorAnalysisAgent", "provider": "baidu", "resource": "places.search", "timestamp": "ISO-8601", "notes": "..." }
```

## 5) Agents: Specs and Functions

### 5.1 LocationIntakeAgent

Responsibilities
- Validate/normalize input, geocode if necessary, attach provider IDs.

Init
```
class LocationIntakeAgent(Agent):
    def __init__(self, config: LocationIntakeConfig, providers: ProviderRegistry, cache: Cache): ...
```

Run
```
def run(self, input_payload: LocationIntakeRequest, context: ExecutionContext) -> dict
```

Inputs
- LocationIntakeRequest

Outputs
```
{
  "location": {
    "location_id": "...",
    "lat": 31.23,
    "lng": 121.47,
    "address": "normalized",
    "provider_refs": [{ "provider": "baidu", "place_id": "..." }]
  },
  "category_norm": { "category": "electronics_retail", "subcategory": "multi_brand" }
}
```

Errors/Notes
- If geocoding ambiguity > threshold, return disambiguation candidates with confidence.

### 5.2 LocationAnalysisAgent

Responsibilities
- Collect base map context, nearby POIs, isochrones seeds.

Init
```
class LocationAnalysisAgent(Agent):
    def __init__(self, config: LocationAnalysisConfig, providers: ProviderRegistry, cache: Cache): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "category_norm": {...}
}
```

Processing
- Nearby POIs by category rings (e.g., 250m, 500m, 1km).
- Isochrones: walk/transit/drive for 5, 10, 15 minutes.
- Identify malls/complex context, floor if available.

Outputs
```
{
  "pois": [PlaceFeature, ...],
  "isochrones": [Catchment, ...],
  "context_features": {
    "mall_context": { "mall_id": "...", "name": "...", "floor": "B1" },
    "street_connectivity_proxy": 0.68
  }
}
```

### 5.3 CustomerAnalysisAgent

Responsibilities
- Estimate demand from residential/daytime population within catchments; compute visit/purchase projections.

Init
```
class CustomerAnalysisAgent(Agent):
    def __init__(self, config: CustomerAnalysisConfig, providers: ProviderRegistry, cache: Cache): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "isochrones": [Catchment, ...],
  "category_norm": {...},
  "pois": [PlaceFeature, ...]
}
```

Processing
- Overlay isochrones with demographics (WorldPop raster for residential; daytime proxies from office/school/mall POI density).
- Gravity/Huff model with electronics-specific larger radius and destination weighting.
- Baseline electronics AOV/conversion assumptions; growth curves for 1y/3y/5y.

Outputs
```
{
  "demand": {
    "catchment_stats": [{ "mode": "transit", "minutes": 15, "population_residential": ..., "daytime_proxy": ... }],
    "visits_estimate": { "current": [low, high], "1y": [...], "3y": [...], "5y": [...] },
    "purchase_estimate": { ... },
    "assumptions": ["electronics low frequency", "destination behavior"]
  }
}
```

### 5.4 CompetitorAnalysisAgent

Responsibilities
- Identify competitors, score attractiveness, estimate their revenue range.

Init
```
class CompetitorAnalysisAgent(Agent):
    def __init__(self, config: CompetitorAnalysisConfig, providers: ProviderRegistry, cache: Cache): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "isochrones": [Catchment, ...],
  "category_norm": {...},
  "pois": [PlaceFeature, ...]
}
```

Processing
- Filter competitor POIs by Chinese taxonomy and brand dictionary (Apple, Xiaomi, Huawei, Suning, Gome, JD stores, camera/computer).
- Compute attractiveness_score: brand weight, reviews (volume/recency/rating), mall anchor, visibility proxies, distance/transit time.
- Estimate revenue: footfall proxy x conversion x AOV; produce ranges and uncertainty.

Outputs
```
{
  "competitors": [Competitor, ...],
  "share_of_choice": [{ "entity": "candidate", "share": 0.35 }, { "entity": "Apple Pudong", "share": 0.18 }, ...],
  "notes": ["Two strong mall anchors within 1km"]
}
```

### 5.5 AccessibilityAnalysisAgent

Responsibilities
- Quantify access/visibility/logistics; align with electronics shopper behavior.

Init
```
class AccessibilityAnalysisAgent(Agent):
    def __init__(self, config: AccessibilityAnalysisConfig, providers: ProviderRegistry, cache: Cache): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "pois": [PlaceFeature, ...],
  "isochrones": [Catchment, ...],
  "competitors": [Competitor, ...],
  "category_norm": {...}
}
```

Processing
- Distances to metro exits, bus stops; corner vs mid-block by street graph geometry; frontage/visibility proxies (POI density on frontage, road class, intersection betweenness).
- Parking and delivery proxies via nearby parking lots, road access.

Outputs
```
{
  "accessibility": AccessibilityScore
}
```

### 5.6 GeneralAnalysisAgent

Responsibilities
- Broader signals: policies, reviews/sentiment, district growth, news.

Init
```
class GeneralAnalysisAgent(Agent):
    def __init__(self, config: GeneralAnalysisConfig, providers: ProviderRegistry, cache: Cache, llm: LLM): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "category_norm": {...},
  "pois": [PlaceFeature, ...]
}
```

Processing
- Web search (Baidu): neighborhood plans, mall leasing norms, any restrictions.
- Review/sentiment summary from available provider metadata.
- LLM to summarize and extract policy insights with citations.

Outputs
```
{
  "market_insights": {
    "policies": [{ "title": "...", "summary": "...", "url": "..." }],
    "sentiment": { "electronics": "generally positive", "service": "mixed" },
    "growth_trends": ["New mall opening Q4 nearby"],
    "citations": [...]
  }
}
```

### 5.7 SynthesisReportAgent

Responsibilities
- Consolidate metrics and qualitative insights into final structured outputs and a narrative. Exports PDF.

Init
```
class SynthesisReportAgent(Agent):
    def __init__(self, config: SynthesisConfig, llm: LLM, renderer: ReportRenderer, validator: MetricValidator): ...
```

Run
```
def run(self, input_payload: dict, context: ExecutionContext) -> dict
```

Inputs
```
{
  "location": {...},
  "demand": {...},
  "competitors": {...},
  "accessibility": AccessibilityScore,
  "market_insights": {...}
}
```

Processing
- Compute quantitative key metrics; perform sanity checks and sensitivity scenarios.
- LLM prompt with structured JSON schema and narrative template.
- Generate PDF via renderer.

Outputs
```
{
  "forecasts": [Forecast, ...],
  "report": ReportBundle,
  "pdf_url": "link-or-bytes"
}
```

## 6) Provider Adapters

### 6.1 BaiduPlacesProvider

Init
```
class BaiduPlacesProvider:
    def __init__(self, api_key: str, http: HttpClient, cache: Cache): ...
```

Functions
```
def geocode(self, address: str) -> { "lat": float, "lng": float, "confidence": float, "raw": dict }

def reverse_geocode(self, lat: float, lng: float) -> { "address": str, "components": dict }

def search(self, query: str, location: (lat, lng), radius_m: int, category_filters: list[str]) -> list[PlaceFeature]

def place_details(self, place_id: str) -> PlaceFeature
```

### 6.2 AMapRoutingProvider

Init
```
class AMapRoutingProvider:
    def __init__(self, api_key: str, http: HttpClient, cache: Cache): ...
```

Functions
```
def travel_time(self, origins: list[(lat,lng)], destination: (lat,lng), mode: str) -> list[float]

def isochrone(self, center: (lat,lng), mode: str, minutes: int) -> GeoJSONPolygon
  # fallback: sampled radial routing -> hull polygon
```

### 6.3 OSMDataProvider

```
class OSMDataProvider:
    def __init__(self, overpass_url: str, cache: Cache): ...

def fetch_pois(self, bbox: BBox, tags: dict[str, list[str]]) -> list[PlaceFeature]
def street_graph_metrics(self, bbox: BBox) -> { "connectivity": float, "corner_candidates": [coords...] }
```

### 6.4 DemographicsProvider (WorldPop)

```
class DemographicsProvider:
    def __init__(self, raster_store: RasterStore): ...

def population_sum(self, polygon_geojson) -> int
```

### 6.5 WebSearchProvider (Baidu)

```
class WebSearchProvider:
    def __init__(self, api_key: str, http: HttpClient, cache: Cache): ...

def search(self, query: str, site_filters: list[str], lang: str) -> list[{ "title": str, "url": str, "snippet": str }]
def fetch_and_extract(self, url: str) -> { "text": str, "lang": str, "title": str }
```

### 6.6 ProviderRegistry

```
class ProviderRegistry:
    def __init__(self, baidu: BaiduPlacesProvider, amap: AMapRoutingProvider, osm: OSMDataProvider, demo: DemographicsProvider, web: WebSearchProvider): ...
```

## 7) Orchestration

Framework
- Prefer Prefect or Dagster for simple observability.

Pipeline entry
```
def run_location_pipeline(request: LocationIntakeRequest, config: PipelineConfig) -> ReportBundle
```

Steps (DAG)
- s1 = LocationIntakeAgent.run(request)
- s2 = LocationAnalysisAgent.run(s1)
- [s3a, s3b] = parallel:
  - s3a = CustomerAnalysisAgent.run({s1, s2})
  - s3b = CompetitorAnalysisAgent.run({s1, s2})
- s4 = AccessibilityAnalysisAgent.run({s1, s2, s3b})
- s5 = GeneralAnalysisAgent.run({s1, s2})
- s6 = SynthesisReportAgent.run({s1, s3a, s3b, s4, s5})

Caching and retries
- Cache provider calls keyed by request signature and version.
- Retry transient provider errors with exponential backoff.

Provenance
- Each agent appends provenance items to outputs.
- run_id + timestamps captured in ExecutionContext.

## 8) Modeling Details (MVP)

Catchments
- Modes: walk (5/10/15 min), transit (10/20/30 min), drive (10/20 min) as available.
- Use AMap isochrones or fallback synthetic.

Demand model (electronics)
- Population within catchments weighted by distance/transit time.
- Propensity lower than QSR; destination weight for malls/anchors.
- Baseline:
  - Conversion rate range: 3–12% (tunable by subcategory/brand).
  - AOV range: 800–1800 CNY (placeholder; configurable).
- Growth assumptions:
  - 1y: soft ramp as awareness builds.
  - 3y: stabilize; competitive reactions.
  - 5y: macro/district trend adjustments.

Competitor attractiveness
- Weighted factors: brand_strength, review_volume, rating, mall_anchor, visibility, distance, price_level.
- Normalize to [0,1]; use multinomial logit for share-of-choice approximation.

Accessibility metrics
- Transit exit distance, street connectivity, corner vs mid-block, frontage/visibility approximations, parking/delivery proxies.

Uncertainty
- Compute per factor coverage; propagate via Monte Carlo or interval arithmetic to produce ranges and confidence.

## 9) LLM Synthesis

LLM: GPT-4o with JSON mode + narrative.

Prompt template (simplified)
```
System: You are a retail location analyst. Produce a concise, data-backed report. Use provided metrics; do not invent numbers.
User content:
- Location summary: ...
- Demand metrics: ...
- Competitors: ...
- Accessibility: ...
- Market insights: ...
Instructions:
- Output JSON strictly matching ReportBundle schema plus narrative_text.
- Include 4 forecast periods (current, 1y, 3y, 5y) and sensitivities (AOV ±10%, competitor +1/-1).
- Cite sources from provenance.
```

Validator
- MetricValidator checks consistency: revenue = visits * conversion * AOV at bounds; units; ranges monotonic where expected.

Renderer
- ReportRenderer builds PDF with key metrics table, charts, and narrative.

## 10) UI and Integration

Modules
- MapSelector: pin drop in Shanghai, address search (Baidu).
- LocationForm: category/subcategory, size, notes.
- RunButton: triggers pipeline; shows progress states per agent.
- ReportViewer: display HTML + PDF export.
- API endpoints:
  - POST /api/run_location
  - GET /api/report/{run_id}

## 11) Configuration and Secrets

Config (YAML or env-based)
- provider.api_keys.baidu
- provider.api_keys.amap
- locales.default_language: en|zh|bilingual
- modeling.defaults.electronics: { AOV_range, conversion_range }
- pipeline.timeouts
- caching.ttl_seconds

Secrets
- Stored in .env or vault; never logged. Redact in provenance.

## 12) Error Handling

- Provider errors: retry with backoff; degrade gracefully with coverage flags.
- Missing data: set uncertainty high; mark data_gaps in report.
- LLM schema mismatch: auto-correct with repair pass or fallback to deterministic summary.

## 13) Evaluation Plan

- Backtest: choose 5–10 known electronics locations in Shanghai; compare predicted vs proxy performance (e.g., review velocity).
- Sensitivity checks: perturb AOV/conversion; ensure narrative updates.
- Robustness: simulate API failures; confirm graceful degradation.

## 14) Extensibility

- Swappable providers via ProviderRegistry.
- New geographies: implement local provider adapters; keep agent logic same.
- New verticals: change modeling config (propensity, AOV, catchment size) and taxonomy mapping.
- Premium data feature flags for future upgrades.

## 15) Open Items

- Output language preference (English/Chinese/bilingual).
- Finalize electronics subcategory defaults and brand dictionary.
- Confirm review sources scope (Baidu-only for MVP).
- Choose orchestration framework (Prefect vs Dagster).

## 16) Appendix: Function Signatures (Consolidated)

Agent constructors
```
LocationIntakeAgent(config: LocationIntakeConfig, providers: ProviderRegistry, cache: Cache)
LocationAnalysisAgent(config: LocationAnalysisConfig, providers: ProviderRegistry, cache: Cache)
CustomerAnalysisAgent(config: CustomerAnalysisConfig, providers: ProviderRegistry, cache: Cache)
CompetitorAnalysisAgent(config: CompetitorAnalysisConfig, providers: ProviderRegistry, cache: Cache)
AccessibilityAnalysisAgent(config: AccessibilityAnalysisConfig, providers: ProviderRegistry, cache: Cache)
GeneralAnalysisAgent(config: GeneralAnalysisConfig, providers: ProviderRegistry, cache: Cache, llm: LLM)
SynthesisReportAgent(config: SynthesisConfig, llm: LLM, renderer: ReportRenderer, validator: MetricValidator)
```

Agent run calls
```
run(input_payload: dict, context: ExecutionContext) -> dict
```

Provider adapters
```
BaiduPlacesProvider.geocode(address: str) -> GeocodeResult
BaiduPlacesProvider.search(query: str, location: (lat,lng), radius_m: int, category_filters: list[str]) -> list[PlaceFeature]
BaiduPlacesProvider.place_details(place_id: str) -> PlaceFeature

AMapRoutingProvider.travel_time(origins: list[(lat,lng)], destination: (lat,lng), mode: str) -> list[float]
AMapRoutingProvider.isochrone(center: (lat,lng), mode: str, minutes: int) -> GeoJSONPolygon

OSMDataProvider.fetch_pois(bbox: BBox, tags: dict[str, list[str]]) -> list[PlaceFeature]
OSMDataProvider.street_graph_metrics(bbox: BBox) -> dict

DemographicsProvider.population_sum(polygon_geojson) -> int

WebSearchProvider.search(query: str, site_filters: list[str], lang: str) -> list[SearchHit]
WebSearchProvider.fetch_and_extract(url: str) -> ExtractedDoc
```

Pipeline
```
run_location_pipeline(request: LocationIntakeRequest, config: PipelineConfig) -> ReportBundle
```

If this structure looks good, I’ll fill in exact JSON Schemas (with $id/$schema), provider-specific category mappings for electronics in CN, and the initial LLM prompt plus example output.