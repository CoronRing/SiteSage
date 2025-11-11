from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

from map_apis.amap import AMap
from map_apis.map_api import MapAPI
from map_apis.type_projection import AMapTypeProjectionAdapter

LOCATION_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "description": "Location payload supporting lat/lng pairs or addresses.",
    "properties": {
        "lat": {"type": "number", "description": "Latitude in decimal degrees."},
        "lng": {"type": "number", "description": "Longitude in decimal degrees."},
        "address": {
            "type": "string",
            "description": "Optional textual description or street address.",
        },
        "label": {
            "type": "string",
            "description": "Optional text label rendered on map overlays.",
        },
    },
    "additionalProperties": True,
}

__all__ = ["MapTool", "LOCATION_SCHEMA"]

class MapTool:
    """
    Map Tool implementation.

    The tool exposes function specifications and callable helpers for:
      * getPlaceInfo
      * getMapVisualization
      * getNearbyPlaces (with type projection via LLM)
      * getDistances
    """

    _PROVIDERS: Dict[str, type[MapAPI]] = {"amap": AMap}

    def __init__(
        self,
        map_choice: str = "amap",
    ) -> None:
        self.provider_name = map_choice.lower()
        self.map_api = self._select_provider(self.provider_name)
        if self.provider_name == "amap":
            self.type_projector = AMapTypeProjectionAdapter()
        else:
            raise NotImplementedError
        self._tool_schemas = self._build_tool_schemas()

    @property
    def tools(self) -> Sequence[Mapping[str, Any]]:
        """Return OpenAI tool declarations for registration."""
        return self._tool_schemas

    def call(self, tool_name: str, arguments: Mapping[str, Any]) -> Any:
        dispatch = {
            "getPlaceInfo": self.getPlaceInfo,
            "getMapVisualization": self.getMapVisualization,
            "getNearbyPlaces": self.getNearbyPlaces,
            "getDistances": self.getDistances,
        }
        if tool_name not in dispatch:
            raise ValueError(f"Unsupported tool invocation: {tool_name}")
        return dispatch[tool_name](**arguments)

    # ------------------------------------------------------------------ #
    # Tool function implementations
    # ------------------------------------------------------------------ #

    def getPlaceInfo(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        extra_params: Optional[MutableMapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        
        return self.map_api.getPlaceInfo(
            address, language=language, extra_params=extra_params
        )

    def getMapVisualization(
        self,
        origin: Mapping[str, Any],
        *,
        overlays: Optional[Iterable[Mapping[str, Any]]] = None,
        style: Optional[str] = None,
    ) -> Mapping[str, Any]:
        
        return self.map_api.getMapVisuailization(
            origin, overlays=overlays, style=style
        )

    def getNearbyPlaces(
        self,
        origin: Mapping[str, Any],
        descriptive_types: Sequence[str],
        *,
        radius: int = 500,
        rank: str = "DISTANCE",
        include_details: bool = False,
        num_pages: int = 2,
    ) -> Sequence[Mapping[str, Any]]:
        
        projected_types = self.type_projector.project_types(descriptive_types)
        return self.map_api.getNearbyPlaces(
            origin,
            projected_types,
            radius=radius,
            rank=rank,
            include_details=include_details,
            num_pages=num_pages,
        )

    def getDistances(
        self,
        origin: Mapping[str, Any],
        destinations: Sequence[Mapping[str, Any]],
        *,
        mode: str = "walk",
        units: str = "metric",
    ) -> Sequence[Mapping[str, Any]]:
        
        return self.map_api.getDistance(
            origin, destinations, mode=mode, units=units
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _select_provider(self, provider_name: str) -> MapAPI:
        try:
            provider_cls = self._PROVIDERS[provider_name]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported map provider '{provider_name}'. "
                f"Available providers: {', '.join(self._PROVIDERS)}"
            ) from exc
        return provider_cls()

    def _build_tool_schemas(self) -> Sequence[Mapping[str, Any]]:
        return [
            {
                "type": "function",
                "name": "getPlaceInfo",
                "description": (
                    "Resolve an address or place description to a normalized map feature "
                    f"using the {self.provider_name} API."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Full address or POI description to geocode.",
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language hint understood by the provider.",
                        },
                        "extra_params": {
                            "type": "object",
                            "description": "Advanced provider-specific parameters.",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["address"],
                },
            },
            {
                "type": "function",
                "name": "getMapVisualization",
                "description": (
                    "Produce a static visualization URL that highlights the origin "
                    "and optional overlay markers."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {**LOCATION_SCHEMA, "description": "Origin to highlight."},
                        "overlays": {
                            "type": "array",
                            "description": "Additional markers or waypoints to overlay.",
                            "items": LOCATION_SCHEMA,
                        },
                        "style": {
                            "type": "string",
                            "description": "Optional provider style identifier.",
                        },
                    },
                    "required": ["origin"],
                },
            },
            {
                "type": "function",
                "name": "getNearbyPlaces",
                "description": (
                    "Search for nearby places using descriptive categories which are "
                    "mapped to provider-specific type codes via an LLM."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {**LOCATION_SCHEMA, "description": "Reference location."},
                        "descriptive_types": {
                            "type": "array",
                            "description": (
                                "Human readable categories such as 'coffee shop' or "
                                "'electric vehicle charging'."
                            ),
                            "items": {"type": "string"},
                        },
                        "radius": {
                            "type": "integer",
                            "description": "Search radius in meters (1-50000).",
                            "default": 500,
                        },
                        "rank": {
                            "type": "string",
                            "description": "Sorting strategy (DISTANCE or WEIGHT).",
                            "default": "DISTANCE",
                        },
                        "include_details": {
                            "type": "boolean",
                            "description": "Request extended provider fields when available.",
                            "default": False,
                        },
                        "num_pages": {
                            "type": "integer",
                            "description": "Maximum number of result pages to fetch.",
                            "default": 5,
                        },
                    },
                    "required": ["origin", "descriptive_types"],
                },
            },
            {
                "type": "function",
                "name": "getDistances",
                "description": "Compute travel distances from an origin to destinations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {**LOCATION_SCHEMA, "description": "Starting location."},
                        "destinations": {
                            "type": "array",
                            "description": "List of destinations to evaluate.",
                            "items": LOCATION_SCHEMA,
                        },
                        "mode": {
                            "type": "string",
                            "description": "Travel mode such as walk, drive, or transit.",
                            "default": "walk",
                        },
                        "units": {
                            "type": "string",
                            "description": "Output units (metric or imperial).",
                            "default": "metric",
                        },
                    },
                    "required": ["origin", "destinations"],
                },
            },
        ]
