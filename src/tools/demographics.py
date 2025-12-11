from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from worldpop_apis.demographics import Demographics, PopulationStats

from tools.map import LOCATION_SCHEMA

__all__ = ["DemographicsTool"]


class DemographicsTool:
    """Tool wrapper exposing population statistics queries."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._demographics = Demographics(data_dir=data_dir)
        self._tool_schemas = self._build_tool_schemas()

    @property
    def tools(self) -> Sequence[Mapping[str, Any]]:
        return self._tool_schemas

    def call(self, tool_name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        dispatch = {"getPopulationStats": self.getPopulationStats}
        if tool_name not in dispatch:
            raise ValueError(f"Unsupported demographics tool '{tool_name}'")
        return dispatch[tool_name](**arguments)

    def getPopulationStats(
        self,
        location: Mapping[str, Any],
        *,
        radius_m: float = 500.0,
        coord_ref: str = "WGS84",
    ) -> Mapping[str, Any]:
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            raise ValueError("location must include numeric 'lat' and 'lng' fields")

        origin = {"lat": float(lat), "lng": float(lng)}
        stats = self._demographics.population_statistics(
            (origin["lat"], origin["lng"]),
            radius_m=float(radius_m),
            coord_ref=coord_ref,
        )
        return self._format_response(origin, float(radius_m), coord_ref, stats)

    def _format_response(
        self,
        origin: Mapping[str, float],
        radius_m: float,
        coord_ref: str,
        stats: PopulationStats,
    ) -> Mapping[str, Any]:
        return {
            "provider": "worldpop",
            "origin": origin,
            "radius_m": radius_m,
            "coordinate_reference": coord_ref,
            "total_population": stats.total_population,
            "age_breakdown": dict(stats.age_breakdown),
            "age_composition": dict(stats.age_composition),
        }

    def _build_tool_schemas(self) -> Sequence[Mapping[str, Any]]:
        return [
            {
                "type": "function",
                "name": "getPopulationStats",
                "description": (
                    "Summarize population counts and age composition within a radius "
                    "around a latitude/longitude point using preloaded worldpop rasters."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            **LOCATION_SCHEMA,
                            "description": (
                                "Origin coordinate. lat and lng must be provided; "
                                "address fields are ignored."
                            ),
                        },
                        "radius_m": {
                            "type": "number",
                            "description": "Search radius in meters.",
                            "default": 500,
                        },
                        "coord_ref": {
                            "type": "string",
                            "description": (
                                "Coordinate reference of the provided lat/lng. Supported: "
                                "WGS84 (default, international standard) or GCJ-02 (Chinese maps)."
                            ),
                            "default": "WGS84",
                        },
                    },
                    "required": ["location"],
                },
            }
        ]
