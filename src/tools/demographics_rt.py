from __future__ import annotations
from typing import Any, Mapping
from tools.demographics import DemographicsTool
import railtracks as rt

demographics_tool = DemographicsTool()

@rt.function_node
def tool_get_population_stats(
    location: Mapping[str, Any],
    *,
    radius: float = 500.0,
    coord_ref: str = "WGS84",
) -> Mapping[str, Any]:
    """
    Summarize population counts and age composition within a radius around a latitude/longitude point using worldpop rasters.

    Args:
        origin (Mapping[str, Any]): Location from which proximity is measured, keys 'lat' and 'lng' are required.
        radius (Optional[float]): Default 500. Search radius in meters. Any numbers bigger than 100 are valid.
        coord_ref (Optional[str]): Default WGS84 (Google Maps standard). Use GCJ-02 for Chinese map services (AMap).

    Returns:
        Mapping[str, Any]: total population, population composition stratified by age (0-14, 15-59, 60-64, 65+).
    """
    if radius is not float:
        return {"error": f"Radius should be a float, not a {type(radius)}"}
            
    return demographics_tool.getPopulationStats(
        location, radius_m=radius, coord_ref=coord_ref
    )
