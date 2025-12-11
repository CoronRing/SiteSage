from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

import requests

from map_apis.map_api import MapAPI

logger = logging.getLogger(__name__)

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "google_maps.log"


def _ensure_google_maps_file_logging() -> None:
    """Attach a file handler for persistent Google Maps logging if missing."""
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == str(_LOG_FILE):
            break
    else:
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)


_ensure_google_maps_file_logging()


def _serialize_for_log(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        return repr(payload)


def _log_function_call(name: str, payload: Mapping[str, Any]) -> None:
    try:
        logger.info("GoogleMaps.%s input=%s", name, _serialize_for_log(payload))
    except Exception:
        logger.info("GoogleMaps.%s input=%s", name, payload)


def _match_place_with_addresses(place: str, addresses: Sequence[str]):
    """Match a place query with a list of candidate addresses using LLM."""
    from openai import OpenAI
    client = OpenAI()
    response = client.responses.create(
        model="gpt-4",
        input=[
            {
                "role": "user",
                "content": f"Within given addresses, find the one match the most with the given place.\naddresses:{addresses}\nplace:{place}\nYou must only output the exact matched address, not any other texts."
            }
        ],
        temperature=0.01
    ).output_text
    if response in addresses:
        return True, response
    else:
        return False, response


class GoogleMaps(MapAPI):
    """Concrete MapAPI adapter backed by Google Maps Platform APIs."""

    BASE_URL = "https://maps.googleapis.com/maps/api"
    GEOCODE_PATH = "/geocode/json"
    PLACE_SEARCH_PATH = "/place/textsearch/json"
    PLACE_NEARBY_PATH = "/place/nearbysearch/json"
    DISTANCE_PATH = "/distancematrix/json"
    STATIC_MAP_PATH = "/staticmap"

    _MODE_TO_TYPE = {
        "drive": "driving",
        "driving": "driving",
        "car": "driving",
        "transit": "transit",
        "bus": "transit",
        "walk": "walking",
        "walking": "walking",
        "bike": "bicycling",
        "bicycle": "bicycling",
    }
    
    # Class-level warning message
    _api_key_warning: Optional[str] = None

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.has_valid_api_key = True
        if not self.api_key:
            warning_msg = (
                "Google Maps API key is missing! "
                "Set GOOGLE_MAPS_API_KEY/GOOGLE_API_KEY environment variable or pass api_key. "
                "Google Maps functionality will be limited. This may be acceptable for Asia/China regions using AMap."
            )
            logger.warning(warning_msg)
            print(f"\n{'='*80}\n⚠️  WARNING: {warning_msg}\n{'='*80}\n", flush=True)
            GoogleMaps._api_key_warning = warning_msg
            self.api_key = "MISSING_API_KEY"  # Set placeholder to avoid None errors
            self.has_valid_api_key = False
        self.session = session or requests.Session()
        self.timeout = timeout
        super().__init__("google_maps")
    
    @classmethod
    def get_api_key_warning(cls) -> Optional[str]:
        """Get the API key warning if one was generated."""
        return cls._api_key_warning

    def getPlaceInfo(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Mapping[str, Any]:
        _log_function_call(
            "getPlaceInfo",
            {
                "address": address,
                "language": language,
                "extra_params": extra_params,
            },
        )
        params: Dict[str, Any] = {
            "query": address,
        }
        if language:
            params["language"] = language
        if extra_params:
            params.update(extra_params)

        payload = self._request(self.PLACE_SEARCH_PATH, params)
        results = payload.get("results") or []
        if not results:
            raise ValueError(f"Google Maps could not find place for: {address!r}")

        # Get top candidates
        top_candidates = results[:min(10, len(results))]
        top_addresses = [r.get("formatted_address", "") for r in top_candidates]
        top_names = [r.get("name", "") for r in top_candidates]
        
        logger.info(f"top results for getPlaceInfo: {top_addresses[:5]} {top_names[:5]}")
        
        matched, response = _match_place_with_addresses(address, top_addresses + top_names)
        if not matched:
            logger.warning(f"No exact match found for address:{address}, using first result")
            record = results[0]
        else:
            target = [i for i, x in enumerate(top_addresses) if x == response]
            if len(target) == 0:
                target = [i for i, x in enumerate(top_names) if x == response]
                if len(target) == 0:
                    logger.warning("Match failed, using first result")
                    record = results[0]
                else:
                    record = top_candidates[target[0]]
            else:
                record = top_candidates[target[0]]

        location = record.get("geometry", {}).get("location", {})
        lat = location.get("lat", 0)
        lng = location.get("lng", 0)

        # Extract types (categories)
        types = record.get("types", [])
        category = types[0] if types else "unknown"
        subcategory = types[1] if len(types) > 1 else None

        result = {
            "provider": self.provider,
            "place_id": record.get("place_id") or f"{lng},{lat}",
            "name": record.get("name") or address,
            "address": record.get("formatted_address"),
            "category": category,
            "subcategory": subcategory,
            "lat": lat,
            "lng": lng,
            "raw": record
        }

        return result

    def getNearbyPlaces(
        self,
        place: Mapping[str, Any] | str,
        types: Sequence[str],
        *,
        radius: int = 500,
        rank: str = "DISTANCE",
        include_details: bool = False,
        num_pages: int = 5,
    ) -> Sequence[Mapping[str, Any]]:
        _log_function_call(
            "getNearbyPlaces",
            {
                "place": place if isinstance(place, str) else dict(place),
                "types": list(types),
                "radius": radius,
                "rank": rank,
                "include_details": include_details,
                "num_pages": num_pages,
            },
        )
        lat, lng = self._resolve_coordinates(place)
        rankby = "distance" if rank.upper() == "DISTANCE" else "prominence"

        base_params: Dict[str, Any] = {
            "location": f"{lat},{lng}",
            "radius": max(1, min(radius, 50000)),
        }
        
        if rankby == "distance":
            # When ranking by distance, radius should not be specified
            base_params.pop("radius")
            base_params["rankby"] = "distance"
        else:
            base_params["rankby"] = "prominence"
        
        # Google Maps uses type (singular) for nearby search
        if types and len(types) > 0:
            # Google only accepts one type at a time for nearby search
            base_params["type"] = types[0]

        results = []
        seen_ids: set[str] = set()
        next_page_token = None

        # Google Maps API limits to 3 pages (60 results max) per search
        max_pages = min(num_pages, 3)

        for page in range(max_pages):
            params = base_params.copy()
            if next_page_token:
                params = {"pagetoken": next_page_token}
                # Small delay required when using pagetoken
                import time
                time.sleep(2)

            payload = self._request(self.PLACE_NEARBY_PATH, params)
            places = payload.get("results") or []
            
            if not places:
                break

            for poi in places:
                place_id = poi.get("place_id")
                if not place_id or place_id in seen_ids:
                    continue
                seen_ids.add(place_id)

                location = poi.get("geometry", {}).get("location", {})
                poi_lat = location.get("lat", 0)
                poi_lng = location.get("lng", 0)
                
                poi_types = poi.get("types", [])

                place_feature: Dict[str, Any] = {
                    "provider": self.provider,
                    "place_id": place_id,
                    "name": poi.get("name"),
                    "category": poi_types[0] if poi_types else "unknown",
                    "subcategory": poi_types[1] if len(poi_types) > 1 else None,
                    "lat": poi_lat,
                    "lng": poi_lng,
                    "rating": self._safe_float(poi.get("rating")),
                    "review_count": self._safe_int(poi.get("user_ratings_total")),
                    "address": poi.get("vicinity") or poi.get("formatted_address"),
                    "raw": poi,
                }

                results.append(place_feature)

            # Check for next page
            next_page_token = payload.get("next_page_token")
            if not next_page_token:
                break

        return results

    def getDistance(
        self,
        origin: Mapping[str, Any] | str,
        destinations: Sequence[Mapping[str, Any] | str],
        *,
        mode: str = "walk",
        units: str = "metric",
    ) -> Sequence[Dict[str, Any]]:
        _log_function_call(
            "getDistance",
            {
                "origin": origin if isinstance(origin, str) else dict(origin),
                "destinations": [d if isinstance(d, str) else dict(d) for d in destinations],
                "mode": mode,
                "units": units,
            },
        )
        origin_lat, origin_lng = self._resolve_coordinates(origin)
        travel_mode = self._MODE_TO_TYPE.get(mode.lower(), "walking")
        unit_system = "imperial" if units.lower() == "imperial" else "metric"

        # Google Distance Matrix API can handle multiple destinations
        dest_coords = []
        for dest in destinations:
            dest_lat, dest_lng = self._resolve_coordinates(dest)
            dest_coords.append(f"{dest_lat},{dest_lng}")

        params = {
            "origins": f"{origin_lat},{origin_lng}",
            "destinations": "|".join(dest_coords),
            "mode": travel_mode,
            "units": unit_system,
        }

        payload = self._request(self.DISTANCE_PATH, params)
        
        rows = payload.get("rows", [])
        if not rows:
            return []

        elements = rows[0].get("elements", [])
        
        results: list[Dict[str, Any]] = []
        for idx, (element, destination) in enumerate(zip(elements, destinations)):
            if element.get("status") != "OK":
                logger.warning(f"Distance calculation failed for destination {idx}: {element.get('status')}")
                continue

            distance = element.get("distance", {})
            duration = element.get("duration", {})
            
            distance_m = distance.get("value", 0)  # meters
            duration_s = duration.get("value", 0)  # seconds

            distance_payload: Dict[str, Any] = {"distance_m": distance_m}
            if units.lower() != "metric":
                distance_payload[f"distance_{units.lower()}"] = distance_m * 0.000621371

            results.append(
                {
                    "origin": {"lat": origin_lat, "lng": origin_lng},
                    "destination": destination,
                    **distance_payload,
                    "duration_s": duration_s,
                    "mode": mode,
                    "raw": element,
                }
            )
        
        return results

    def getMapVisuailization(
        self,
        origin: Mapping[str, Any] | str,
        *,
        zoom: Optional[Any] = 15,
        overlays: Optional[Iterable[Mapping[str, Any]]] = None,
        style: Optional[str] = None,
    ) -> Mapping[str, Any]:
        _log_function_call(
            "getMapVisuailization",
            {
                "origin": origin,
                "zoom": zoom,
                "overlays": list(overlays) if overlays else None,
                "style": style,
            },
        )
        lat, lng = self._resolve_coordinates(origin)

        # Build markers string for Google Static Maps API
        markers = [f"color:red|label:A|{lat},{lng}"]
        overlay_details = []
        
        if overlays:
            for index, overlay in enumerate(overlays, start=1):
                o_lat, o_lng = self._resolve_coordinates(overlay)
                label = overlay.get("label") or chr(65 + (index % 26))  # B, C, D, etc.
                markers.append(f"color:blue|label:{label}|{o_lat},{o_lng}")
                overlay_details.append(
                    {"label": label, "lat": o_lat, "lng": o_lng, "raw": overlay}
                )

        params = {
            "center": f"{lat},{lng}",
            "zoom": zoom,
            "size": "512x512",
            "markers": markers,
            "key": self.api_key,
        }
        
        if style:
            params["style"] = style

        # Build URL
        base_url = f"{self.BASE_URL}{self.STATIC_MAP_PATH}"
        
        safe_params = {k: v for k, v in params.items() if k != "key"}
        safe_params["markers"] = markers

        # Build full URL
        request = requests.Request("GET", base_url, params=params)
        prepared = self.session.prepare_request(request)

        return {
            "provider": self.provider,
            "url": prepared.url,
            "query_params": safe_params,
            "origin": {"lat": lat, "lng": lng, "label": "origin"},
            "overlays": overlay_details,
        }

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        merged_params = {"key": self.api_key, **params}
        safe_params = {k: v for k, v in merged_params.items() if k != "key"}
        logger.info("Google Maps request path=%s params=%s", path, safe_params)
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}{path}", params=merged_params, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Google Maps HTTP error path=%s params=%s error=%s", path, safe_params, exc
            )
            raise

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error(
                "Google Maps JSON decode error path=%s params=%s error=%s body=%s",
                path,
                safe_params,
                exc,
                response.text,
            )
            raise

        status = payload.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            error_message = payload.get("error_message", "unknown error")
            logger.error(
                "Google Maps API error path=%s params=%s status=%s message=%s payload=%s",
                path,
                safe_params,
                status,
                error_message,
                payload,
            )
            raise RuntimeError(f"Google Maps API error: {status} - {error_message}")
        
        return payload

    def _resolve_coordinates(self, place: Mapping[str, Any] | str) -> tuple[float, float]:
        # Handle string address directly
        if isinstance(place, str):
            resolved = self.getPlaceInfo(place)
            return float(resolved["lat"]), float(resolved["lng"])
        
        # Handle dict with lat/lng
        if "lat" in place and "lng" in place:
            return float(place["lat"]), float(place["lng"])
        if "location" in place and isinstance(place["location"], dict):
            return float(place["location"]["lat"]), float(place["location"]["lng"])
        if "address" in place:
            resolved = self.getPlaceInfo(str(place["address"]))
            return float(resolved["lat"]), float(resolved["lng"])
        raise ValueError("Place must include lat/lng or address for Google Maps operations.")

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value in (None, "", "null"):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            if value in (None, "", "null"):
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None
