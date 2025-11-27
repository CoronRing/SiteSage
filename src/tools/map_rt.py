from __future__ import annotations

import railtracks as rt

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

from tools.map import MapTool

map_nearby_places_cache = []

map_tool = MapTool()

def clean_map_cache():
    global map_nearby_places_cache
    map_nearby_places_cache = []
    
@rt.function_node
def tool_get_place_info(
    address: str,
    city: str
) -> Mapping[str, Any]:
    """
    Resolve a textual address or POI description into a normalized provider record.
    Args:
        address (str): string of address, do not put city, if in China, you must put district name before the road name (e.g. in China: 天河区体育西路21号)
        city (str): string of city name.

    Returns:
        Mapping[str, Any]: Place information, including lat, lon.
    """
    return map_tool.getPlaceInfo(
        address,
        extra_params={"city":city}
    )

@rt.function_node
def tool_get_map_visualization(
    origin: Mapping[str, Any],
    *,
    zoom: Optional[int] = 14,
    overlays: Optional[Iterable[Mapping[str, Any]]] = None,
    style: Optional[str] = None,
) -> Mapping[str, Any]:
    """
    Produce a static visualization (e.g., a map image URL) for the supplied geometry.
    Args:
        origin (Mapping[str, Any]): Primary location that is highlighted, should include lat, lng, or address (only when you don't know lat, lng), the origin point will be labeled as 'origin' on map.
        zoom (Optional[int]): Zoom in extent, default as 14, select span between (12-15), higher digit means more zoom in.
        overlays (Optional[Iterable[Mapping[str, Any]]]): Additional markers to render, maximum 10 overlays, each should include lat, lng, or address (only when you don't know lat, lng), and label for the name in map.
        style (Optional[str]): Provider-specific style identifier for the visualization.

    Returns:
        Mapping[str, Any]: Visualization payload, including url.
    """
    return map_tool.getMapVisualization(
        origin, zoom=zoom, overlays=overlays, style=style
    )

@rt.function_node
def tool_get_nearby_places(
    origin: Mapping[str, Any],
    descriptive_types: Sequence[str],
    *,
    radius: int = 500,
    rank: str = "DISTANCE",
    num_pages: int = 2,
) -> Sequence[Mapping[str, Any]]:
    """
    Retrieve nearby places by projecting descriptive categories to provider-specific types.
    Args:
        origin (Mapping[str, Any]): Primary location that is searched on, should include lat, lng, or address (only when you don't know lat, lng).
        descriptive_types (Sequence[str]): Human-readable categories to search for.
        radius (Optional[int]): Search radius in meters, default 500, minimal 500.
        rank (Optional[str]): Provider-supported ranking strategy, choose from "DISTANCE" and "WEIGHT".
        num_pages (Optional[int]): Maximum number of pagination pages (25 results each page) to traverse, default 2.

    Returns:
        Sequence[Mapping[str, Any]]: Ordered list of nearby place payloads.
    """

    nearby_places = map_tool.getNearbyPlaces(
        origin,
        descriptive_types,
        radius=radius,
        rank=rank,
        num_pages=num_pages,
    )
    global map_nearby_places_cache
    map_nearby_places_cache.extend([str(x) for x in nearby_places])
    map_nearby_places_cache = list(set(map_nearby_places_cache))
    return nearby_places

@rt.function_node
def tool_get_distances(
    origin: Mapping[str, Any],
    destinations: Sequence[Mapping[str, Any]],
    *,
    mode: str = "walk"
) -> Sequence[Mapping[str, Any]]:
    """
    Compute travel distance metrics from an origin to one or more destinations.
    Args:
        origin (Mapping[str, Any]): Starting location for the route calculation, should include lat, lng, or address (only when you don't know lat, lng).
        destinations (Sequence[Mapping[str, Any]]): Target endpoints to evaluate, same requirement as origin.
        mode (Optional[str]): Travel mode (walk, drive, transit, etc.), default walk.

    Returns:
        Sequence[Mapping[str, Any]]: Distance and duration payloads per destination.
    """
    return map_tool.getDistances(
        origin, destinations, mode=mode
    )
