# sitesage_backend.py

from __future__ import annotations

import dotenv
dotenv.load_dotenv()

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from openai import OpenAI
import railtracks as rt
from ddgs import DDGS  # pip install ddgs

rt.set_config(save_state=True)

# Project-provided wrappers
from tools.map_rt import (
    tool_get_distances,
    tool_get_map_visualization,
    tool_get_nearby_places,
    tool_get_place_info,
    clean_map_cache,
    get_map_cache
)

from tools.demographics_rt import tool_get_population_stats

# Prompts
from prompts.agent_prompts import (
    UNDERSTANDING_AGENT_SYSTEM,
    CUSTOMER_AGENT_SYSTEM,
    TRAFFIC_AGENT_SYSTEM,
    COMPETITION_AGENT_SYSTEM,
    WEIGHTING_AGENT_SYSTEM,
    EVALUATION_AGENT_SYSTEM,
    EVALUATION_SEPARATE_AGENT_SYSTEM,
    FINAL_REPORT_AGENT_SYSTEM,
    get_understanding_prompt,
    get_customer_prompt,
    get_traffic_prompt,
    get_competition_prompt,
    get_weighting_prompt,
    get_evaluation_prompt,
    get_final_report_prompt,
)


# -----------------------------------------------------------------------------
# Logging (module logger; frontend config controls console/file)
# -----------------------------------------------------------------------------
def _configure_logging(filename='logger') -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(processName)s] %(message)s",
                        datefmt="%H:%M:%S",
                        force=True,
                        filename='logs/' + filename + '.log')
    rt.set_config(log_file='logs/' + filename + '.log')
_configure_logging("sitesage")
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


def osm_static_map_url(lat: float, lng: float, zoom: int = 16, width: int = 600, height: int = 400, transform: bool = True) -> str:
    if transform:
        from worldpop_apis.coordTransform.coordTransform_utils import gcj02_to_wgs84
        lng, lat = gcj02_to_wgs84(lng, lat)
    marker = f"markers={lat},{lng},lightblue1"
    return (
        "https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lng}&zoom={zoom}&size={width}x{height}&{marker}"
    )


_openai_client: Optional[OpenAI] = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def extract_location_info(place: Mapping[str, Any]) -> Dict[str, Any]:
    location: Dict[str, Any] = {}
    lat, lng = extract_lat_lng(place)
    location["lat"] = lat
    location["lng"] = lng

    address = ""
    if isinstance(place, Mapping):
        address = place.get("address") or place.get("formatted_address") or ""
    if address:
        location["address"] = address
    else:
        logger.error("Extract location infor failed to extract address from:%s", str(place))
    
    return location


def _summarize_text(system_prompt: str, report: str) -> str:
    if not report:
        return ""
    client = _get_openai_client()
    try:
        response = client.responses.create(
            model="gpt-5.1",
            reasoning={"effort": "low"},
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": report}],
                },
            ],
        )
    except Exception as exc:
        logger.warning("Failed to summarize report: %s", exc)
        return report
    return response.output_text


def summarize_understanding_report(report: str) -> str:
    system_prompt = (
        "You should summarize the information that user input of a location report, "
        "the output should be a paragraph, stating street context, surrounding context, "
        "and relative locations. You don't need to extract the address, coordinates, "
        "and anything related to store itself. Show less descriptive expression, keep more facts. "
        "Directly output the summarized paragraph."
    )
    return _summarize_text(system_prompt, report)


def summarize_report(report: str, report_type: str = "") -> str:
    system_prompt = (
        "You should summarize the information from a {} analysis report for a store in a location, "
        "the output should be no more than 3 paragraphs. Show less descriptive expression, keep more facts, "
        "places and digits. Directly output the summarized paragraphs.".format(report_type)
    )
    return _summarize_text(system_prompt, report)


def fix_json_error(text: str) -> str:
    client = _get_openai_client()
    try:
        response = client.responses.create(
            model="gpt-5.1",
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Here is a Json string with some problems, please fix the error in the json, "
                                f"and return the fixed json. Input: {text} \nDirectly return the fixed json."
                            ),
                        }
                    ],
                }
            ],
        )
    except Exception as exc:
        logger.error("Failed to fix JSON error: %s", exc)
        return text
    return response.output_text


# -----------------------------------------------------------------------------
# Extra Tools exposed to the agents
# -----------------------------------------------------------------------------
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
# Agents (with prompts from prompts.py)
# -----------------------------------------------------------------------------
def make_understanding_agent() -> Any:
    system = rt.llm.SystemMessage(UNDERSTANDING_AGENT_SYSTEM)
    return rt.agent_node(
        name="UnderstandingAgent",
        tool_nodes=(tool_get_place_info, tool_get_map_visualization),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
        max_tool_calls=12,
    )


def make_customer_agent() -> Any:
    system = rt.llm.SystemMessage(CUSTOMER_AGENT_SYSTEM)
    return rt.agent_node(
        name="CustomerAgent",
        tool_nodes=(tool_get_population_stats, tool_get_nearby_places, tool_web_search),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
        max_tool_calls=12,
    )


def make_traffic_agent() -> Any:
    system = rt.llm.SystemMessage(TRAFFIC_AGENT_SYSTEM)
    return rt.agent_node(
        name="TrafficAgent",
        tool_nodes=(tool_get_place_info, tool_get_nearby_places, tool_web_search, tool_get_map_visualization),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
        max_tool_calls=16,
    )


def make_competition_agent() -> Any:
    system = rt.llm.SystemMessage(COMPETITION_AGENT_SYSTEM)
    return rt.agent_node(
        name="CompetitionAgent",
        tool_nodes=(tool_get_place_info, tool_get_nearby_places, tool_web_search, tool_get_map_visualization),
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
        max_tool_calls=16,
    )


def run_weighting_agent(weighting_prompt: str) -> str:
    """
    Call the weighting agent directly using the OpenAI client instead of RailTracks.

    Returns the raw response text that is expected to be JSON according to the prompt.
    """
    client = _get_openai_client()
    response = client.responses.create(
        model="gpt-5.1",
        temperature=0.01,
        input=[
            {"role": "system", "content": WEIGHTING_AGENT_SYSTEM},
            {
                "role": "user",
                "content": [{"type": "input_text", "text": weighting_prompt}],
            },
        ],
    )
    return response.output_text


def run_evaluation_agent(
        customer_report: str,
        traffic_report: str,
        competition_report: str,
        customer_rubric: str,
        traffic_rubric: str,
        competition_rubric: str) -> Any:
    """
    Evaluation agent that scores the three analysis reports using rubrics.
    Returns JSON with scores for customer, traffic, and competition.
    """
    user_prompt = """Evaluate the analysis report using the provided rubrics. Score objectively and provide detailed justifications.

---

ANALYSIS REPORT:
{report}

SCORING RUBRIC:
{rubric}

---

Evaluate report according to its rubric. Return the JSON with scores and justifications."""
    
    client = _get_openai_client()
    def _run(report, rubric):
        response = client.responses.create(
            model="gpt-5.1",
            reasoning={"effort": "low"},
            input=[
                {"role": "system", "content": EVALUATION_SEPARATE_AGENT_SYSTEM},
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt.format(report=report, rubric=rubric)}],
                },
            ],
        )
        try:
            payload = parse_json_from_text(response.output_text)
        except Exception as e:
            print("error in parsing revision, try again ...", e)
            payload = parse_json_from_text(fix_json_error(response.output_text))
        return payload
    
    return {
        "customer": _run(customer_report, customer_rubric),
        "traffic": _run(traffic_report, traffic_rubric),
        "competition": _run(competition_report, competition_rubric),
    }


def make_evaluation_agent():
    system = rt.llm.SystemMessage(EVALUATION_AGENT_SYSTEM)
    return rt.agent_node(
        name="EvaluationAgent",
        tool_nodes=(),  # no tools
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
    )


def make_final_report_agent() -> Any:
    """
    Final narrative report agent (no tools).
    Synthesizes the three analysis reports into a polished final report.
    """
    system = rt.llm.SystemMessage(FINAL_REPORT_AGENT_SYSTEM)
    return rt.agent_node(
        name="FinalReportAgent",
        tool_nodes=(),  # no tools
        system_message=system,
        llm=rt.llm.OpenAILLM("gpt-5.1"),
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

    # clean map cache
    clean_map_cache()

    # 1) Understanding
    understanding_agent = make_understanding_agent()
    understanding_prompt = get_understanding_prompt(prompt)
    with rt.Session(logging_setting="VERBOSE", timeout=600.0):
        resp = await rt.call(understanding_agent, user_input=understanding_prompt)
    
    try:
        ujson = parse_json_from_text(resp.text)
    except Exception as e:
        logger.error("Failed to parse understanding agent response as JSON, retry...: %s", e)
        try:
            ujson = parse_json_from_text(fix_json_error(resp.text))
        except:
            logger.error("Failed to parse understanding agent response as JSON again: %s, %s", e, resp.text)
            # raise ValueError("Failed to parse understanding json")
            ujson = {}

    assets["reports"]["01_understanding"] = write_markdown(
        session_dir, "01_understanding", ujson.get("report_md", "# Understanding")
    )

    # extract store and location information
    store_info = dict(ujson.get("store_info", {}))
    place = dict(ujson.get("place", {}))
    location_info = extract_location_info(place)
    location_description = summarize_understanding_report(ujson.get("report_md", ""))
    if location_description:
        location_info["description"] = location_description
    logger.info(f"session {session_id}: store_info: {store_info}, location_info: {location_info}")

    # prefer deterministic OSM static map so frontend always has an image
    # map_image_url = ujson.get("map_image_url", "")
    map_image_url = osm_static_map_url(location_info['lat'], location_info['lng'])

    # 2) Customer
    customer_agent = make_customer_agent()
    customer_prompt = get_customer_prompt(store_info, location_info)
    with rt.Session(logging_setting="VERBOSE", timeout=600.0):
        cresp = await rt.call(customer_agent, user_input=customer_prompt)
    
    # Extract the markdown report (the entire response is the report)
    customer_report = cresp.text.strip()
    assets["reports"]["02_customer"] = write_markdown(
        session_dir, "02_customer", customer_report
    )
    customer_context = summarize_report(customer_report, "customer")

    # 3) Traffic - receives Customer report
    traffic_agent = make_traffic_agent()
    traffic_prompt = get_traffic_prompt(store_info, location_info, customer_context)
    with rt.Session(logging_setting="VERBOSE", timeout=600.0):
        tresp = await rt.call(traffic_agent, user_input=traffic_prompt)
    
    # Extract the markdown report
    traffic_report = tresp.text.strip()
    assets["reports"]["03_traffic"] = write_markdown(
        session_dir, "03_traffic", traffic_report
    )
    traffic_context = summarize_report(traffic_report, "traffic")

    # 4) Competition - receives Customer and Traffic reports
    competition_agent = make_competition_agent()
    competition_prompt = get_competition_prompt(
        store_info,
        location_info,
        customer_context,
        traffic_context,
    )
    with rt.Session(logging_setting="VERBOSE", timeout=600.0):
        kresp = await rt.call(competition_agent, user_input=competition_prompt)
    
    # Extract the markdown report
    competition_report = kresp.text.strip()
    assets["reports"]["04_competition"] = write_markdown(
        session_dir, "04_competition", competition_report
    )

    # 5) Weighting (logically parallel to evaluation - does NOT receive scores)
    weighting_response_text = ""

    # Load weighting rubric
    rubric_dir = os.path.abspath("rubrics")
    try:
        with open(os.path.join(rubric_dir, "weighting_rubric.md"), "r", encoding="utf-8") as f:
            weighting_rubric = f.read()
    except Exception as e:
        logger.error("Failed to load weighting_rubric.md: %s", e)
        weighting_rubric = ""
    
    weighting_prompt = get_weighting_prompt(store_info, weighting_rubric)
    try:
        weighting_response_text = run_weighting_agent(weighting_prompt)
    except Exception as exc:
        logger.error("Weighting agent call failed: %s", exc)
        weighting_response_text = ""
    
    if weighting_response_text:
        try:
            wjson = parse_json_from_text(weighting_response_text)
        except Exception as e:
            logger.error("Failed to parse weighting agent response as JSON, retry...: %s", e)
            try:
                wjson = parse_json_from_text(fix_json_error(weighting_response_text))
            except Exception as e:
                logger.error("Failed to parse weighting agent response as JSON again: %s", e)
                wjson = {}
    else:
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

    # 6) Evaluation - score the three analysis reports using rubrics
    # NOTE: Evaluation is logically parallel to Weighting:
    #   - Weighting (Step 5) determines importance based on BUSINESS CONTEXT (store type, model)
    #   - Evaluation (Step 6) determines quality based on ANALYSIS RUBRICS (how well analysis was done)
    #   - Weighting does NOT receive evaluation scores to avoid bias
    #   - This ensures weights reflect business priorities, not analysis quality
    
    # Load rubric files
    rubric_dir = os.path.abspath("rubrics")
    try:
        with open(os.path.join(rubric_dir, "customer_rubric.md"), "r", encoding="utf-8") as f:
            customer_rubric = f.read()
    except Exception as e:
        logger.error("Failed to load customer_rubric.md: %s", e)
        customer_rubric = "# Customer Rubric\nNo rubric available."
    
    try:
        with open(os.path.join(rubric_dir, "traffic_rubric.md"), "r", encoding="utf-8") as f:
            traffic_rubric = f.read()
    except Exception as e:
        logger.error("Failed to load traffic_rubric.md: %s", e)
        traffic_rubric = "# Traffic Rubric\nNo rubric available."
    
    try:
        with open(os.path.join(rubric_dir, "competition_rubric.md"), "r", encoding="utf-8") as f:
            competition_rubric = f.read()
    except Exception as e:
        logger.error("Failed to load competition_rubric.md: %s", e)
        competition_rubric = "# Competition Rubric\nNo rubric available."
    
    # old version: use rt evaluation agent to evaluate all reports at once
    # evaluation_agent = make_evaluation_agent()
    # evaluation_prompt = get_evaluation_prompt(
    #     customer_report=customer_report,
    #     traffic_report=traffic_report,
    #     competition_report=competition_report,
    #     customer_rubric=customer_rubric,
    #     traffic_rubric=traffic_rubric,
    #     competition_rubric=competition_rubric,
    # )
    
    # with rt.Session(logging_setting="VERBOSE", timeout=600.0):
    #     eresp = await rt.call(evaluation_agent, user_input=evaluation_prompt)
    
    # try:
    #     ejson = parse_json_from_text(eresp.text)
    # except Exception as e:
    #     logger.error("Failed to parse evaluation agent response as JSON, retry...: %s", e)
    #     try:
    #         fixed = fix_json_error(eresp.text)
    #         ejson = parse_json_from_text(fixed)
    #     except Exception as inner:
    #         logger.error("Failed to parse evaluation agent response as JSON again: %s, %s", inner, eresp.text)
    #         # raise ValueError("Failed to parse evaluation json")
    #         ejson = {}

    # new version: evaluate reports one by one
    ejson = run_evaluation_agent(
        customer_report=customer_report,
        traffic_report=traffic_report,
        competition_report=competition_report,
        customer_rubric=customer_rubric,
        traffic_rubric=traffic_rubric,
        competition_rubric=competition_rubric
    )
    
    # Extract scores
    evaluation_scores = {
        "customer": ejson.get("customer", {"score": 0.0, "justification": ""}),
        "traffic": ejson.get("traffic", {"score": 0.0, "justification": ""}),
        "competition": ejson.get("competition", {"score": 0.0, "justification": ""}),
    }
    
    # Calculate final weighted score
    customer_score = float(evaluation_scores["customer"].get("score", 0.0))
    traffic_score = float(evaluation_scores["traffic"].get("score", 0.0))
    competition_score = float(evaluation_scores["competition"].get("score", 0.0))
    final_score = (wc * customer_score) + (wt * traffic_score) + (wk * competition_score)
    
    assets["reports"]["05_evaluation"] = write_markdown(
        session_dir, "05_evaluation", 
        f"# Evaluation Scores\n\n"
        f"## Customer Analysis: {customer_score:.1f}/10\n{evaluation_scores['customer'].get('justification', '')}\n\n"
        f"## Traffic & Accessibility: {traffic_score:.1f}/10\n{evaluation_scores['traffic'].get('justification', '')}\n\n"
        f"## Competition Analysis: {competition_score:.1f}/10\n{evaluation_scores['competition'].get('justification', '')}\n\n"
        f"## Final Weighted Score: {final_score:.1f}/10\n"
        f"Weights: Customer={wc:.2f}, Traffic={wt:.2f}, Competition={wk:.2f}"
    )

    # 7) Final Report (no tools) - synthesizes the three analysis reports with scores
    final_agent = make_final_report_agent()
    final_prompt = get_final_report_prompt(
        session_id=session_id,
        prompt=prompt,
        store_info=store_info,
        place=place,
        customer_report=customer_report,
        traffic_report=traffic_report,
        competition_report=competition_report,
        evaluation_scores=evaluation_scores,
        weights=weights,
        final_score=final_score,
    )
    with rt.Session(logging_setting="VERBOSE", timeout=600.0):
        fresp = await rt.call(final_agent, user_input=final_prompt)
    
    try:
        fjson = parse_json_from_text(fresp.text)
    except Exception as e:
        logger.error("Failed to parse final agent response as JSON: %s", e)
        fjson = {}
    
    final_report_md = fjson.get("report_md", "# Final Report\n\nNo content.")
    final_report_path = write_markdown(session_dir, "07_final_report", final_report_md)
    assets["reports"]["07_final_report"] = final_report_path
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
        "reports": {
            "customer": customer_report,
            "traffic": traffic_report,
            "competition": competition_report,
        },
        "scores": {
            "customer": customer_score,
            "traffic": traffic_score,
            "competition": competition_score,
        },
        "weights": weights,
        "final_score": final_score,
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
    print(f"Final Score: {res['final_score']:.2f} (computed by final agent)")
    print("Weights:", {k: round(v, 2) for k, v in res["weights"].items() if isinstance(v, float)})
    print("Map:", res["assets"].get("map_image_url", ""))
    print("Final Report:", res["final_report"].get("report_path", ""))
    print("Reports saved under:", os.path.abspath(os.path.join("save", res['session_id'])))
    print("\nAnalysis Reports:")
    print("  - Customer:", res["assets"]["reports"].get("02_customer", ""))
    print("  - Traffic:", res["assets"]["reports"].get("03_traffic", ""))
    print("  - Competition:", res["assets"]["reports"].get("04_competition", ""))
    if res["errors"]:
        print("Errors:", res["errors"])
    else:
        print("Errors: none")
        
if __name__ == "__main__":
    main()
