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
_LOG_FILE = _LOG_DIR / "amap.log"


def _ensure_amap_file_logging() -> None:
    """Attach a file handler for persistent AMap logging if missing."""
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


_ensure_amap_file_logging()


def _serialize_for_log(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        return repr(payload)


def _log_function_call(name: str, payload: Mapping[str, Any]) -> None:
    try:
        logger.info("AMap.%s input=%s", name, _serialize_for_log(payload))
    except Exception:
        logger.info("AMap.%s input=%s", name, payload)

def _match_place_with_addresses(place: str, addresses: Sequence[str]):
    from openai import OpenAI
    client = OpenAI()
    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": f"within given addresses, find the one match the most with the given place.\naddresss:{addresses}\nplace:{place}\nYou must only output the matched address."
            }
        ]
    ).output_text
    if response in addresses:
        return True, response
    else:
        return False, response

class AMap(MapAPI):
    """Concrete MapAPI adapter backed by AMap (Gaode) REST services."""

    BASE_URL = "https://restapi.amap.com"
    GEOCODE_PATH = "/v3/geocode/geo"
    PLACE_TEXT_PATH = "/v3/place/text"
    PLACE_AROUND_PATH = "/v5/place/around"
    DISTANCE_PATH = "/v3/distance"
    STATIC_MAP_PATH = "/v3/staticmap"

    _MODE_TO_TYPE = {
        "drive": "0",
        "driving": "0",
        "car": "0",
        "transit": "1",
        "bus": "1",
        "walk": "3",
        "walking": "3",
        "bike": "2",
        "bicycle": "2",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("AMAP_API_KEY") or os.getenv("AMAP_KEY")
        if not self.api_key:
            raise ValueError(
                "AMap API key is required. Set AMAP_API_KEY/AMAP_KEY or pass api_key."
            )
        self.session = session or requests.Session()
        self.timeout = timeout
        super().__init__("amap")

    def getPlaceInfo_v1(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Mapping[str, Any]:
        _log_function_call(
            "getPlaceInfov1",
            {
                "address": address,
                "language": language,
                "extra_params": extra_params,
            },
        )
        params: Dict[str, Any] = {
            "address": address,
            "output": "JSON",
            "extensions": "all",
        }
        if language:
            params["language"] = language
        if extra_params:
            params.update(extra_params)

        payload = self._request(self.GEOCODE_PATH, params)
        geocodes = payload.get("geocodes") or []
        if not geocodes:
            raise ValueError(f"AMap could not geocode address: {address!r}")

        record = geocodes[0]
        lng, lat = self._parse_location(record.get("location"))

        return {
            "provider": self.provider,
            "place_id": record.get("adcode") or record.get("id") or f"{lng},{lat}",
            "name": record.get("formatted_address") or address,
            "category": (record.get("type") or "").split(";")[0] or "unknown",
            "subcategory": (record.get("type") or "").split(";")[1] if ";" in (record.get("type") or "") else None,
            "lat": lat,
            "lng": lng,
            "raw": record,
        }
    
    def getPlaceInfo(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        top_k: int = 5 # top-k result will be returned
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
            "keywords": address,
            "output": "JSON",
            "extensions": "all",
        }
        if language:
            params["language"] = language
        if extra_params:
            params.update(extra_params)

        payload = self._request(self.PLACE_TEXT_PATH, params)
        pois = payload.get("pois") or []
        if not pois:
            raise ValueError(f"AMap could not find POI for: {address!r}")

        top_5_addresses = [poi.get("address") for poi in pois[:5]]
        matched, response = _match_place_with_addresses(address, top_5_addresses)
        if not matched:
            logger.error(f"No matching found for address:{address}, {top_5_addresses}, {response}")
            raise ValueError(f"AMap could not find POI for: {address!r} due to matching issue, response:{response}")
        
        record = pois[[i for i, x in enumerate(top_5_addresses) if x == response][0]]

        lng, lat = self._parse_location(record.get("location"))

        # Category/type string like: "购物服务;百货商场;百货商场"
        type_str = record.get("type") or ""
        parts = type_str.split(";") if type_str else []

        category = parts[0] if len(parts) > 0 else "unknown"
        subcategory = parts[1] if len(parts) > 1 else None

        result = {
            "provider": self.provider,
            "place_id": record.get("id") or record.get("adcode") or f"{lng},{lat}",
            "name": record.get("name") or address,
            "address": record.get("address"),
            "category": category,
            "subcategory": subcategory,
            "lat": lat,
            "lng": lng,
            "raw": record
        }

        return result

    def getNearbyPlaces(
        self,
        place: Mapping[str, Any],
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
                "place": dict(place),
                "types": list(types),
                "radius": radius,
                "rank": rank,
                "include_details": include_details,
                "num_pages": num_pages,
            },
        )
        lat, lng = self._resolve_coordinates(place)
        sortrule = "distance" if rank.upper() == "DISTANCE" else "weight"
        total_pages = max(1, min(num_pages, 100))

        base_params: Dict[str, Any] = {
            "location": f"{lng},{lat}",
            "radius": max(1, min(radius, 50000)),
            "sortrule": sortrule,
            "page_size": 25,
            "output": "JSON",
        }
        if types:
            base_params["types"] = "|".join(types)
        if include_details:
            base_params["show_fields"] = "business"

        results = []
        seen_ids: set[str] = set()

        for page in range(1, total_pages + 1):
            params = {**base_params, "page_num": page}
            payload = self._request(self.PLACE_AROUND_PATH, params)
            pois = payload.get("pois") or []
            if not pois:
                break
            for poi in pois:
                poi_types = (poi.get("typecode") or "").split("|")
                poi_lng, poi_lat = self._parse_location(poi.get("location"))
                place_id = (
                    poi.get("id")
                    or poi.get("parentid")
                    or poi.get("official_id")
                    or f"{poi_lng},{poi_lat}"
                )
                if place_id in seen_ids:
                    continue
                seen_ids.add(place_id)

                place_feature: Dict[str, Any] = {
                    "provider": self.provider,
                    "place_id": place_id,
                    "name": poi.get("name"),
                    "category": poi_types[0] if poi_types and poi_types[0] else poi.get("type"),
                    "subcategory": poi_types[1] if len(poi_types) > 1 else None,
                    "lat": poi_lat,
                    "lng": poi_lng,
                    "rating": self._safe_float(poi.get("rating")),
                    "review_count": self._safe_int(poi.get("comment_num")),
                    "address": poi.get("address"),
                    "raw": poi,
                }

                results.append(place_feature)

            if len(pois) < base_params["page_size"]:
                break

        return results

    def getDistance(
        self,
        origin: Mapping[str, Any],
        destinations: Sequence[Mapping[str, Any]],
        *,
        mode: str = "walk",
        units: str = "metric",
    ) -> Sequence[Dict[str, Any]]:
        _log_function_call(
            "getDistance",
            {
                "origin": dict(origin),
                "destinations": [dict(d) for d in destinations],
                "mode": mode,
                "units": units,
            },
        )
        origin_lat, origin_lng = self._resolve_coordinates(origin)
        transport_type = self._MODE_TO_TYPE.get(mode.lower(), "0")

        results: list[Dict[str, Any]] = []
        for destination in destinations:
            dest_lat, dest_lng = self._resolve_coordinates(destination)
            params = {
                "origins": f"{origin_lng},{origin_lat}",
                "destination": f"{dest_lng},{dest_lat}",
                "type": transport_type,
                "output": "JSON",
            }
            payload = self._request(self.DISTANCE_PATH, params)
            entries = payload.get("results") or []
            if not entries:
                continue
            entry = entries[0]
            distance_m = float(entry.get("distance", 0))
            duration_s = float(entry.get("duration", 0))
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
                    "raw": entry,
                }
            )
        return results

    def getMapVisuailization(
        self,
        origin: Mapping[str, Any],
        *,
        zoom: Optional[Any] = 15,
        overlays: Optional[Iterable[Mapping[str, Any]]] = None,
        style: Optional[str] = None,
    ) -> Mapping[str, Any]:
        _log_function_call(
            "getMapVisuailization",
            {
                "origin": dict(origin),
                "zoom": zoom,
                "overlays": [dict(o) for o in overlays] if overlays else None,
                "style": style,
            },
        )
        lat, lng = self._resolve_coordinates(origin)

        marker_parts = [f"mid,,A:{lng},{lat}"]
        overlay_details = []
        if overlays:
            for index, overlay in enumerate(overlays, start=1):
                o_lat, o_lng = self._resolve_coordinates(overlay)
                label = overlay.get("label") or chr(65 + ((index - 1) % 26))
                marker_parts.append(f"mid,,{label}:{o_lng},{o_lat}")
                overlay_details.append(
                    {"label": label, "lat": o_lat, "lng": o_lng, "raw": overlay}
                )

        params = {
            "location": f"{lng},{lat}",
            "zoom": zoom,
            "size": "512*512",
            "markers": "|".join(marker_parts),
            "key": self.api_key,
        }
        if style:
            params["styles"] = style

        request = requests.Request(
            "GET",
            f"{self.BASE_URL}{self.STATIC_MAP_PATH}",
            params=params,
        )
        prepared = self.session.prepare_request(request)

        safe_params = {k: v for k, v in params.items() if k != "key"}

        return {
            "provider": self.provider,
            "url": prepared.url,
            "query_params": safe_params,
            "origin": {"lat": lat, "lng": lng, 'label': 'origin'},
            "overlays": overlay_details,
        }

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        merged_params = {"key": self.api_key, **params}
        safe_params = {k: v for k, v in merged_params.items() if k != "key"}
        logger.info("AMap request path=%s params=%s", path, safe_params)
        try:
            response = self.session.get(
                f"{self.BASE_URL}{path}", params=merged_params, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "AMap HTTP error path=%s params=%s error=%s", path, safe_params, exc
            )
            raise

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error(
                "AMap JSON decode error path=%s params=%s error=%s body=%s",
                path,
                safe_params,
                exc,
                response.text,
            )
            raise

        if payload.get("status") != "1":
            info = payload.get("info") or "unknown error"
            logger.error(
                "AMap API error path=%s params=%s info=%s payload=%s",
                path,
                safe_params,
                info,
                payload,
            )
            raise RuntimeError(f"AMap API error: {info}" + json.dumps(payload))
        return payload

    def _parse_location(self, location: Optional[str]) -> tuple[float, float]:
        if not location:
            raise ValueError("AMap response missing location coordinates.")
        lng_str, lat_str = location.split(",", 1)
        return float(lng_str), float(lat_str)

    def _resolve_coordinates(self, place: Mapping[str, Any]) -> tuple[float, float]:
        if "lat" in place and "lng" in place:
            return float(place["lat"]), float(place["lng"])
        if "location" in place and isinstance(place["location"], str):
            lng, lat = self._parse_location(place["location"])
            return lat, lng
        if "address" in place:
            resolved = self.getPlaceInfo(str(place["address"]))
            return float(resolved["lat"]), float(resolved["lng"])
        raise ValueError("Place must include lat/lng or address for AMap operations.")

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
