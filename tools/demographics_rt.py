from __future__ import annotations

from typing import Any, Mapping

from tools.demographics import DemographicsTool

demographics_tool = DemographicsTool()

def getPopulationStats(
    location: Mapping[str, Any],
    *,
    radius_m: float = 500.0,
    coord_ref: str = "GCJ-02",
) -> Mapping[str, Any]:
    """
    Summarize population counts and age composition within a radius around a latitude/longitude point using preloaded worldpop rasters.

    Args:
        origin (Mapping[str, Any]): Location from which proximity is measured, keys 'lat' and 'lon' are required.
        radius (float): Default 500. Search radius in meters.
    """
    return demographics_tool.getPopulationStats(
        location, radius_m=radius_m, coord_ref=coord_ref
    )
