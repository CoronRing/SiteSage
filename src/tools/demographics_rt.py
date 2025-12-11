from __future__ import annotations
from typing import Any, Mapping
from tools.demographics import DemographicsTool
from tools.map_rt import map_tool
import railtracks as rt

demographics_tool = DemographicsTool()

@rt.function_node
def tool_get_population_stats(
    location: Mapping[str, Any] | str,
    *,
    radius: float = 500.0,
    coord_ref: str = "WGS84",
) -> Mapping[str, Any]:
    """
    Summarize population counts and age composition within a radius around a latitude/longitude point using worldpop rasters.

    Args:
        location (Mapping[str, Any] or str): Location from which proximity is measured. Can be a dict with 'lat' and 'lng' keys, a dict with 'address' key, or a plain address string.
        radius (Optional[float]): Default 500. Search radius in meters. Any numbers bigger than 100 are valid.
        coord_ref (Optional[str]): Default WGS84 (Google Maps standard). Use GCJ-02 for Chinese map services (AMap).

    Returns:
        Mapping[str, Any]: total population, population composition stratified by age (0-14, 15-59, 60-64, 65+).
    """
    if not isinstance(radius, (int, float)):
        return {"error": f"Radius should be a number, not a {type(radius)}"}
    
    # Convert string address to coordinates
    if isinstance(location, str):
        place_info = map_tool.getPlaceInfo(location)
        location = {"lat": place_info["lat"], "lng": place_info["lng"]}
    elif isinstance(location, dict) and "address" in location and ("lat" not in location or "lng" not in location):
        place_info = map_tool.getPlaceInfo(location["address"])
        location = {"lat": place_info["lat"], "lng": place_info["lng"]}
            
    return demographics_tool.getPopulationStats(
        location, radius_m=radius, coord_ref=coord_ref
    )

