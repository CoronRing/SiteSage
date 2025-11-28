from __future__ import annotations

import railtracks as rt

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, List

from tools.map import MapTool

import csv
from io import StringIO

place_keys = ["name", "lat", "lng", "distance", "type"]
map_nearby_places_cache = set()

map_tool = MapTool()

def clean_map_cache():
    global map_nearby_places_cache
    map_nearby_places_cache = set()

def get_map_cache():
    return '\n'.join(['\t'.join(place_keys)] + list(map_nearby_places_cache))

def postprocess_nearby_place(place: Mapping[str, Any]) -> Mapping[str, Any]:
    return {k: place[k] for k in place_keys}

def write_map_cache(places: Sequence[Mapping[str, Any]]):
    global map_nearby_places_cache
    for place in places:
        val = "\t".join([str(place[k]) for k in place_keys])
        map_nearby_places_cache.add(val)

@rt.function_node
def tool_get_place_info(
    address: str,
    city: str
) -> Mapping[str, Any]:
    """
    Search place information (such as lat/lng) based on address.
    Args:
        address (str): string of address, do not put city, if in China, you must put district name before the road name (e.g. in China: 天河区体育西路21号)
        city (str): string of city name.

    Returns:
        Dict: Place information, including lat, lng.
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
    Render a provider static map (url) centered on the origin and optional overlay markers
    Args:
        origin (Dict): Primary location, should include 'lat', 'lng', or 'address' (only when you don't know lat, lng), its label will be 'A' on the map.
        zoom (Optional[int]): Zoom in extent, default as 14, select span between 12-17: Lower values show more district-wide context, higher values zoom in to street/building detail.
        overlays (Optional[List[Dict]]): Additional markers to render except for origin, maximum 10 overlays, each should include lat, lng, (or address only when you don't know lat, lng), and label (you can only use 1-character labels such as A,B,C,...).
        style (Optional[str]): Provider-specific style identifier for the visualization.

    Returns:
        Dict: Visualization payload, including url, the origin point will be labeled as 'A'.
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
) -> List[Mapping[str, Any]]:
    """
    Retrieve nearby places by projecting descriptive categories to provider-specific types.
    Args:
        origin (Dict): Primary location that is searched on, should include lat, lng, or address (only when you don't know lat, lng).
        descriptive_types (List[str]): List of categories to search for.
        radius (Optional[int]): Search radius in meters, default 500, minimal 500.
        rank (Optional[str]): Provider-supported ranking strategy, choose from "DISTANCE" and "WEIGHT".
        num_pages (Optional[int]): Maximum number of pagination pages (25 results each page) to traverse, default 2.

    Returns:
        List[Dict]: Ordered list of nearby place dict (keys: name, lat, lng, distance, type).
    """

    nearby_places = map_tool.getNearbyPlaces(
        origin,
        descriptive_types,
        radius=radius,
        rank=rank,
        num_pages=num_pages,
    )
    write_map_cache(nearby_places)
    nearby_places = [postprocess_nearby_place(p) for p in nearby_places]
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
        origin (Dict): Starting location for the route calculation, should include lat, lng, or address (only when you don't know lat, lng).
        destinations (List[Dict]): Target endpoints to evaluate, same requirement as origin.
        mode (Optional[str]): Travel mode (walk, drive, transit, etc.), default walk.

    Returns:
        List[Dict]: Distance and duration payloads per destination.
    """
    return map_tool.getDistances(
        origin, destinations, mode=mode
    )
