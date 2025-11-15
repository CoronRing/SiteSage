# sitesage_backend.py
"""
SiteSage Agentic Prototype Backend (Single File, Robust Tools + Final Report)
==============================================================================

Implements the 5+1 step agentic pipeline with tools the LLM can call iteratively:
1) Understanding (extract store info, geocode, static map)
2) Customer (population metrics)
3) Traffic (transit/parking accessibility)
4) Competition (competitor density)
5) Weighting (derive weights and final score)
6) Final Report (LLM, no tools): human-readable markdown, rationale, and recommendation

Logging:
- Console of the backend can be quiet; detailed per-session logs are handled by the frontend.
- This module focuses on the agent pipeline and report generation.

Main API:
- run_sitesage_session_async(session_id: str, prompt: str, *, language: str = "en") -> dict
- run_sitesage_session(session_id: str, prompt: str, *, language: str = "en") -> dict

Result schema (dict):
- session_id (str)
- input (dict): {prompt: str, language: str}
- store_info (dict): fields include
    - store_type (str)
    - business_description (str)
    - service_mode (str)
    - target_customers (List[str])
    - price_level (str)
    - time_window (str)
    - location_query (str)
- place (dict): provider place payload with normalized lat/lng/lon when available
- features (dict):
    - customer (dict): {radius_m: float, population_total: float|None, age_buckets: Mapping|None, notes: str|None}
    - traffic (dict): {nearby_counts: Mapping, distances: Mapping, nearest_transit: Mapping, notes: str|None}
    - competition (dict): {competitor_counts: Mapping, nearest_competitor: Mapping, notes: str|None}
- scores (dict): per area -> {score: float, justification: str}
- weights (dict): {customer: float, traffic: float, competition: float, justification: str}
- final_score (float)
- final_report (dict):
    - title (str): Title of the final report
    - recommendation (str): Concise recommendation statement
    - highlights (List[str]): Key bullet points
    - report_path (str): Path to saved markdown
- assets (dict): {reports: Mapping[str, str], map_image_url: str}
- errors (List[str])
- timestamps (dict): {started_at: str, ended_at: str}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import railtracks as rt
from ddgs import DDGS  # pip install ddgs

# Project-provided wrappers
from tools.map_rt import (
    getPlaceInfo,
    getNearbyPlaces,
    getDistances,
)
from tools.demographics_rt import getPopulationStats
import dotenv
dotenv.load_dotenv()


# -----------------------------------------------------------------------------
# Logging (module logger; frontend config controls console/file)
# -----------------------------------------------------------------------------
logger = logging.getLogger("sitesage")


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def ensure_session_dir(session_id: str) -> str:
    base = os.path.abspath("save")
    path = os.path.join(base, session_id)
    os.makedirs(path, exist_ok=True)
    return path


def write_markdown(session_dir: str, name: str, content: str) -> str:
    filepath = os.path.join(session_dir, f"{name}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Saved markdown: %s", filepath)
    return filepath


def parse_json_from_text(text: str) -> Any:
    if not isinstance(text, str):
        raise ValueError("Expected string for JSON parsing")
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1).strip())
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str) and v.strip():
            return float(v.strip())
    except Exception:
        return None
    return None


def extract_lat_lng(obj: Mapping[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    candidates = [
        ("lat", "lng"),
        ("lat", "lon"),
        ("latitude", "longitude"),
    ]
    for la, lo in candidates:
        lat = _as_float(obj.get(la))
        lng = _as_float(obj.get(lo))
        if lat is not None and lng is not None:
            return lat, lng

    for k in ("location", "position", "point", "center"):
        sub = obj.get(k)
        if isinstance(sub, Mapping):
            for la, lo in candidates:
                lat = _as_float(sub.get(la))
                lng = _as_float(sub.get(lo))
                if lat is not None and lng is not None:
                    return lat, lng

    geom = obj.get("geometry")
    if isinstance(geom, Mapping):
        loc = geom.get("location")
        if isinstance(loc, Mapping):
            for la, lo in candidates:
                lat = _as_float(loc.get(la))
                lng = _as_float(loc.get(lo))
                if lat is not None and lng is not None:
                    return lat, lng

    # recursive last resort
    def scan(x: Any) -> Tuple[Optional[float], Optional[float]]:
        if isinstance(x, Mapping):
            for la, lo in candidates:
                lat = _as_float(x.get(la))
                lng = _as_float(x.get(lo))
                if lat is not None and lng is not None:
                    return lat, lng
            for v in x.values():
                lt, ln = scan(v)
                if lt is not None and ln is not None:
                    return lt, ln
        elif isinstance(x, list):
            for it in x:
                lt, ln = scan(it)
                if lt is not None and ln is not None:
                    return lt, ln
        return None, None

    return scan(obj)


def normalize_geo(d: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(d) if isinstance(d, Mapping) else {}
    lat, lng = extract_lat_lng(out)
    if lat is not None and lng is not None:
        out["lat"] = lat
        out["lng"] = lng
        out["lon"] = lng
    return out


def normalize_types(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, bool):
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, (list, tuple)):
        out: List[str] = []
        for x in val:
            if isinstance(x, str):
                s = x.strip()
                if s:
                    out.append(s)
        return out
    return []


def osm_static_map_url(lat: float, lng: float, zoom: int = 16, width: int = 600, height: int = 400) -> str:
    marker = f"markers={lat},{lng},lightblue1"
    return (
        "https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lng}&zoom={zoom}&size={width}x{height}&{marker}"
    )


# -----------------------------------------------------------------------------
# Tools exposed to the agents (robust signatures and normalization)
# -----------------------------------------------------------------------------
@rt.function_node
def tool_get_place_info(
    address: Optional[str] = None,
    *,
    query: Optional[str] = None,
    language: Optional[str] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    addr = address or query
    if not addr:
        raise ValueError("address or query is required")
    place = getPlaceInfo(addr, language=language, extra_params=extra_params)
    lat, lng = extract_lat_lng(place)
    if lat is not None and lng is not None:
        place["lat"], place["lng"], place["lon"] = lat, lng, lng
    return place


@rt.function_node
def tool_get_nearby_places(
    origin: Optional[Dict[str, Any]] = None,
    *,
    location: Optional[Dict[str, Any]] = None,
    descriptive_types: Optional[Sequence[str]] = None,
    types: Optional[Sequence[str]] = None,
    radius: int = 500,
    rank: str = "DISTANCE",
    include_details: bool = False,
    num_pages: int = 2,
    pages: Optional[int] = None,
) -> List[Dict[str, Any]]:
    ori = normalize_geo(origin or location or {})
    if "lat" not in ori or "lng" not in ori:
        raise ValueError("origin/location must include lat and lng/lon")

    dt = normalize_types(descriptive_types) or normalize_types(types)
    if not dt:
        logger.warning("tool_get_nearby_places: empty descriptive types; returning empty list")
        return []

    n_pages = int(pages or num_pages or 1)
    return list(
        getNearbyPlaces(
            ori,
            dt,
            radius=radius,
            rank=rank,
            include_details=include_details,
            num_pages=n_pages,
        )
    )


@rt.function_node
def tool_get_distances(
    origin: Optional[Dict[str, Any]] = None,
    *,
    location: Optional[Dict[str, Any]] = None,
    destinations: Sequence[Dict[str, Any]] = (),
    mode: str = "walk",
    units: str = "metric",
) -> List[Dict[str, Any]]:
    ori = normalize_geo(origin or location or {})
    dests = [normalize_geo(d) for d in list(destinations)]
    if "lat" not in ori or "lng" not in ori:
        raise ValueError("origin/location must include lat and lng/lon")
    if not dests:
        return []
    return list(getDistances(ori, dests, mode=mode, units=units))


@rt.function_node
def tool_get_population_stats(
    location: Optional[Dict[str, Any]] = None,
    *,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    lon: Optional[float] = None,
    radius_m: float = 500.0,
    coord_ref: str = "GCJ-02",
) -> Dict[str, Any]:
    loc = normalize_geo(location or {"lat": lat, "lng": lng or lon, "lon": lng or lon})
    if "lat" not in loc or "lng" not in loc:
        raise ValueError("location must include numeric 'lat' and 'lng' (or 'lon') fields")

    raw = getPopulationStats(loc, radius_m=radius_m, coord_ref=coord_ref)
    return {
        "provider": raw.get("provider", "worldpop"),
        "origin": {"lat": loc["lat"], "lng": loc["lng"]},
        "radius_m": float(radius_m),
        "coordinate_reference": coord_ref,
        "population_total": raw.get("population_total") or raw.get("total_population"),
        "age_buckets": raw.get("age_buckets") or raw.get("age_breakdown"),
        "notes": raw.get("notes"),
    }


@rt.function_node
def tool_build_static_map(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    *,
    origin: Optional[Dict[str, Any]] = None,
    location: Optional[Dict[str, Any]] = None,
    zoom: int = 16,
    width: int = 600,
    height: int = 400,
) -> str:
    if lat is None or lng is None:
        o = normalize_geo(origin or location or {})
        lat, lng = extract_lat_lng(o)
    if lat is None or lng is None:
        raise ValueError("lat/lng or origin/location with lat/lng is required")
    return osm_static_map_url(lat, lng, zoom=zoom, width=width, height=height)


@rt.function_node
def tool_web_search(query: str, max_results: int = 5, region: str = "wt-wt") -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region=region, max_results=max_results):
            rows.append(
                {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            )
    return rows


# -----------------------------------------------------------------------------
# Agents (with tool usage guides)
# -----------------------------------------------------------------------------
def make_understanding_agent() -> Any:
    guide = """
Tool usage guide:
- tool_get_place_info(address:str[, language:str]) -> dict (place with lat/lng)
- tool_build_static_map(lat:float, lng:float[, zoom:int,width:int,height:int]) -> str (URL)
Return ONLY JSON:
{
  "store_info": {...},
  "place": {...},
  "map_image_url": "https://...",
  "report_md": "markdown"
}
"""
    system = rt.llm.SystemMessage(
        "You extract structured store info and resolve the place. "
        "Use the tools iteratively if needed. " + guide
    )
    return rt.agent_node(
        name="UnderstandingAgent",
        tool_nodes=(tool_get_place_info, tool_build_static_map),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
        max_tool_calls=12,
    )


def make_customer_agent() -> Any:
    guide = """
Tool usage guide:
- tool_get_population_stats(location: {lat,lng}[, radius_m:float, coord_ref:str]) -> {
    provider, origin, radius_m, coordinate_reference, population_total, age_buckets, notes
  }
You may try multiple radius_m values (e.g., 300, 500, 1000, 1500).
Return ONLY JSON:
{
  "features": {"radius_m": float, "population_total": float|null, "age_buckets": object|null, "notes": str|null},
  "score": float, "justification": "string", "report_md": "markdown"
}
"""
    system = rt.llm.SystemMessage(
        "You analyze nearby customers using population rasters. "
        "Iterate calls if necessary for better radius." + guide
    )
    return rt.agent_node(
        name="CustomerAgent",
        tool_nodes=(tool_get_population_stats,),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
        max_tool_calls=12,
    )


def make_traffic_agent() -> Any:
    guide = """
Tool usage guide:
- tool_get_nearby_places(origin:{lat,lng}, descriptive_types:List[str], radius:int[, rank:str, include_details:bool, num_pages:int]) -> List[dict]
  Aliases: you can also pass 'types' instead of 'descriptive_types'; 'pages' instead of 'num_pages'.
- tool_get_distances(origin:{lat,lng}, destinations:[{lat,lng}], mode:str="walk", units:str="metric") -> List[dict]
Suggested categories: ["subway_station","metro_station","bus_station","bus_stop","parking","parking_lot"].
Try different radius and num_pages if initial results are sparse.
Return ONLY JSON:
{
  "features": {
    "nearby_counts": {...},
    "distances": {"nearest_transit_m": float|null},
    "nearest_transit": {"lat": float, "lon": float, "distance_m": float} | {},
    "notes": str|null
  },
  "score": float, "justification": "string", "report_md": "markdown"
}
"""
    system = rt.llm.SystemMessage(
        "You analyze access and traffic using POIs and distances. " + guide
    )
    return rt.agent_node(
        name="TrafficAgent",
        tool_nodes=(tool_get_nearby_places, tool_get_distances),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
        max_tool_calls=16,
    )


def make_competition_agent() -> Any:
    guide = """
Tool usage guide:
- tool_get_nearby_places(origin:{lat,lng}, descriptive_types:List[str], radius:int[, num_pages:int]) -> List[dict]
- tool_get_distances(origin:{lat,lng}, destinations:[{lat,lng}]) -> List[dict]
Use categories: ["coffee_shop","cafe"]. Adjust radius/pages to differentiate counts (e.g., 500/1000/1500m).
Return ONLY JSON:
{
  "features": {
    "competitor_counts": {"r500": int, "r1000": int, "r1500": int},
    "nearest_competitor": {"lat": float, "lon": float, "distance_m": float} | {},
    "notes": str|null
  },
  "score": float, "justification": "string", "report_md": "markdown"
}
"""
    system = rt.llm.SystemMessage(
        "You analyze competition density and proximity. " + guide
    )
    return rt.agent_node(
        name="CompetitionAgent",
        tool_nodes=(tool_get_nearby_places, tool_get_distances),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
        max_tool_calls=16,
    )


def make_weighting_agent() -> Any:
    guide = """
Return ONLY JSON:
{
  "weights": {"customer": float, "traffic": float, "competition": float},
  "justification": "string",
  "report_md": "markdown"
}
Weights must be non-negative and sum to ~1. Adjust based on store concept.
"""
    system = rt.llm.SystemMessage(
        "You derive weights for customer, traffic, competition from store description and area scores. " + guide
    )
    return rt.agent_node(
        name="WeightingAgent",
        tool_nodes=(),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
    )


def make_final_report_agent() -> Any:
    """
    Final narrative report agent (no tools).
    Produces a polished markdown report with executive summary, key findings,
    weight rationale, recommendation, and appendix of key metrics.
    """
    guide = """
Return ONLY JSON:
{
  "title": "string",
  "recommendation": "string",
  "highlights": ["string", "..."],
  "report_md": "markdown"
}
The report_md must be comprehensive and readable:
- Executive Summary (final score, verdict)
- Site Overview (address/area context; include a short description)
- Customer Insights (population, age buckets; link to business goals)
- Traffic & Accessibility (transit proximity; access modes)
- Competition Landscape (density counts, nearest competitor; positioning)
- Weighting Rationale (why these weights for this concept)
- Recommendation (actionable next steps and risks)
- Appendix (key numbers; reference to saved step reports if helpful)
Keep it concise but informative; use bullet lists and short paragraphs.
"""
    system = rt.llm.SystemMessage(
        "You are a business location analyst writing a final report for a coffee shop site selection. "
        "Use the provided structured data to produce a polished markdown report. " + guide
    )
    return rt.agent_node(
        name="FinalReportAgent",
        tool_nodes=(),  # no tools
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-4o"),
    )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
async def run_sitesage_session_async(
    session_id: str,
    prompt: str,
    *,
    language: str = "en",
) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    session_dir = ensure_session_dir(session_id)
    errors: List[str] = []
    assets: Dict[str, Any] = {"reports": {}}

    # 1) Understanding
    understanding_agent = make_understanding_agent()
    understanding_prompt = (
        "Extract store info and resolve the place. Use tools as needed and return the required JSON.\n"
        f"User request:\n{prompt}"
    )
    with rt.Session(logging_setting="NONE"):
        resp = await rt.call(understanding_agent, user_input=understanding_prompt)
    
    try:
        ujson = parse_json_from_text(resp.text)
    except Exception as e:
        logger.error("Failed to parse understanding agent response as JSON: %s", e)
        ujson = {}
    
    assets["reports"]["01_understanding"] = write_markdown(
        session_dir, "01_understanding", ujson.get("report_md", "# Understanding")
    )
    store_info = dict(ujson.get("store_info", {}))
    place = dict(ujson.get("place", {}))
    map_image_url = ujson.get("map_image_url", "")

    lat, lng = extract_lat_lng(place)
    if lat is not None and lng is not None:
        place["lat"], place["lng"], place["lon"] = lat, lng, lng
        if not map_image_url:
            map_image_url = osm_static_map_url(lat, lng)

    # 2) Customer
    customer_agent = make_customer_agent()
    c_input = {
        "store_info": store_info,
        "place": place,
        "hint": "Try 300m/500m/1000m if needed. End with the JSON schema."
    }
    with rt.Session(logging_setting="NONE"):
        cresp = await rt.call(customer_agent, user_input=json.dumps(c_input, ensure_ascii=False))
    
    try:
        cjson = parse_json_from_text(cresp.text)
    except Exception as e:
        logger.error("Failed to parse customer agent response as JSON: %s", e)
        cjson = {}
    
    assets["reports"]["02_customer"] = write_markdown(
        session_dir, "02_customer", cjson.get("report_md", "# Customer")
    )
    customer_features = dict(cjson.get("features", {}))
    customer_score = float(cjson.get("score", 0.0))
    customer_just = str(cjson.get("justification", ""))

    # 3) Traffic
    traffic_agent = make_traffic_agent()
    t_input = {
        "store_info": store_info,
        "place": place,
        "suggested_types": ["subway_station", "metro_station", "bus_station", "bus_stop", "parking", "parking_lot"],
    }
    with rt.Session(logging_setting="NONE"):
        tresp = await rt.call(traffic_agent, user_input=json.dumps(t_input, ensure_ascii=False))
    
    try:
        tjson = parse_json_from_text(tresp.text)
    except Exception as e:
        logger.error("Failed to parse traffic agent response as JSON: %s", e)
        tjson = {}
    
    assets["reports"]["03_traffic"] = write_markdown(
        session_dir, "03_traffic", tjson.get("report_md", "# Traffic")
    )
    traffic_features = dict(tjson.get("features", {}))
    traffic_score = float(tjson.get("score", 0.0))
    traffic_just = str(tjson.get("justification", ""))

    # 4) Competition
    competition_agent = make_competition_agent()
    k_input = {
        "store_info": store_info,
        "place": place,
        "suggested_types": ["coffee_shop", "cafe"],
    }
    with rt.Session(logging_setting="NONE"):
        kresp = await rt.call(competition_agent, user_input=json.dumps(k_input, ensure_ascii=False))
    
    try:
        kjson = parse_json_from_text(kresp.text)
    except Exception as e:
        logger.error("Failed to parse competition agent response as JSON: %s", e)
        kjson = {}
    
    assets["reports"]["04_competition"] = write_markdown(
        session_dir, "04_competition", kjson.get("report_md", "# Competition")
    )
    competition_features = dict(kjson.get("features", {}))
    competition_score = float(kjson.get("score", 0.0))
    competition_just = str(kjson.get("justification", ""))

    # 5) Weighting
    weighting_agent = make_weighting_agent()
    w_input = {
        "store_info": store_info,
        "area_scores": {
            "customer": {"score": customer_score, "justification": customer_just},
            "traffic": {"score": traffic_score, "justification": traffic_just},
            "competition": {"score": competition_score, "justification": competition_just},
        },
    }
    with rt.Session(logging_setting="NONE"):
        wresp = await rt.call(weighting_agent, user_input=json.dumps(w_input, ensure_ascii=False))
    
    try:
        wjson = parse_json_from_text(wresp.text)
    except Exception as e:
        logger.error("Failed to parse weighting agent response as JSON: %s", e)
        wjson = {}
    
    assets["reports"]["05_weighting"] = write_markdown(
        session_dir, "05_weighting", wjson.get("report_md", "# Weighting")
    )
    weights_raw = dict(wjson.get("weights", {}))
    wc = float(weights_raw.get("customer", 0.33))
    wt = float(weights_raw.get("traffic", 0.33))
    wk = float(weights_raw.get("competition", 0.34))
    total = wc + wt + wk
    if total > 0:
        wc, wt, wk = wc / total, wt / total, wk / total
    weights = {"customer": wc, "traffic": wt, "competition": wk, "justification": wjson.get("justification", "")}

    final_score = customer_score * wc + traffic_score * wt + competition_score * wk

    # 6) Final Report (no tools)
    final_agent = make_final_report_agent()
    final_payload = {
        "session_id": session_id,
        "input": {"prompt": prompt, "language": language},
        "store_info": store_info,
        "place": place,
        "features": {
            "customer": customer_features,
            "traffic": traffic_features,
            "competition": competition_features,
        },
        "scores": {
            "customer": {"score": customer_score, "justification": customer_just},
            "traffic": {"score": traffic_score, "justification": traffic_just},
            "competition": {"score": competition_score, "justification": competition_just},
        },
        "weights": weights,
        "final_score": final_score,
        "assets": {"map_image_url": map_image_url},
        "reports": assets["reports"],
        "guidance": "Write a polished, executive-friendly final report."
    }
    with rt.Session(logging_setting="NONE"):
        fresp = await rt.call(final_agent, user_input=json.dumps(final_payload, ensure_ascii=False))
    
    try:
        fjson = parse_json_from_text(fresp.text)
    except Exception as e:
        logger.error("Failed to parse final agent response as JSON: %s", e)
        fjson = {}
    
    final_report_md = fjson.get("report_md", "# Final Report\n\nNo content.")
    final_report_path = write_markdown(session_dir, "06_final_report", final_report_md)
    assets["reports"]["06_final_report"] = final_report_path
    final_report = {
        "title": fjson.get("title", "SiteSage Final Report"),
        "recommendation": fjson.get("recommendation", ""),
        "highlights": fjson.get("highlights", []),
        "report_path": final_report_path,
    }

    ended_at = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "input": {"prompt": prompt, "language": language},
        "store_info": store_info,
        "place": place,
        "features": {
            "customer": customer_features,
            "traffic": traffic_features,
            "competition": competition_features,
        },
        "scores": {
            "customer": {"score": customer_score, "justification": customer_just},
            "traffic": {"score": traffic_score, "justification": traffic_just},
            "competition": {"score": competition_score, "justification": competition_just},
        },
        "weights": weights,
        "final_score": float(final_score),
        "final_report": final_report,
        "assets": {"reports": assets["reports"], "map_image_url": map_image_url},
        "errors": errors,
        "timestamps": {"started_at": started_at, "ended_at": ended_at},
    }


def run_sitesage_session(session_id: str, prompt: str, *, language: str = "en") -> Dict[str, Any]:
    return asyncio.run(run_sitesage_session_async(session_id, prompt, language=language))


def main() -> None:
    """
    Example run for the SiteSage agentic backend with final report.
    """
    example_prompt = (
        "Open a boutique coffee shop with a cozy vibe targeting young professionals and students. "
        "Strong morning traffic is desired. The location is near 南京东路300号, 黄浦区, 上海."
    )
    res = run_sitesage_session("demo_session", example_prompt, language="zh")

    print("\n=== SiteSage Agentic Summary ===")
    print(f"Session: {res['session_id']}")
    print(f"Final Score: {res['final_score']:.2f} / 10")
    print("Weights:", {k: round(v, 2) for k, v in res["weights"].items() if isinstance(v, float)})
    print("Area Scores:", {k: round(v['score'], 2) for k, v in res["scores"].items()})
    print("Map:", res["assets"].get("map_image_url", ""))
    print("Final Report:", res["final_report"].get("report_path", ""))
    print("Reports saved under:", os.path.abspath(os.path.join("save", res['session_id'])))
    if res["errors"]:
        print("Errors:", res["errors"])
    else:
        print("Errors: none")
        
if __name__ == "__main__":
    main()