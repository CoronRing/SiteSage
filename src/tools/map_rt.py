from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

from tools.map import MapTool

map_tool = MapTool()

def getPlaceInfo(
    address: str,
    *,
    language: Optional[str] = None,
    extra_params: Optional[MutableMapping[str, Any]] = None,
) -> Mapping[str, Any]:
    """
    Resolve a textual address or POI description into a normalized provider record.
    Args:
        address (str): Full address or POI description to geocode.
        language (Optional[str]): Optional language hint understood by the provider.
        extra_params (Optional[MutableMapping[str, Any]]): Advanced provider-specific overrides.

    Returns:
        Mapping[str, Any]: Provider response describing the place.
    """
    return map_tool.getPlaceInfo(
        address, language=language, extra_params=extra_params
    )

def getMapVisualization(
    origin: Mapping[str, Any],
    *,
    zoom: Optional[int] = 14,
    overlays: Optional[Iterable[Mapping[str, Any]]] = None,
    style: Optional[str] = None,
) -> Mapping[str, Any]:
    """
    Produce a static visualization (e.g., a map image URL) for the supplied geometry.
    Args:
        origin (Mapping[str, Any]): Primary location that must be highlighted.
        zoom (Optional[int]): Zoom in extent, default as 14, select span between (12-15), higher digit means more zoom in.
        overlays (Optional[Iterable[Mapping[str, Any]]]): Additional markers or paths to render.
        style (Optional[str]): Provider-specific style identifier for the visualization.

    Returns:
        Mapping[str, Any]: Visualization payload such as URLs or metadata.
    """
    return map_tool.getMapVisuailization(
        origin, zoom=zoom, overlays=overlays, style=style
    )

def getNearbyPlaces(
    origin: Mapping[str, Any],
    descriptive_types: Sequence[str],
    *,
    radius: int = 500,
    rank: str = "DISTANCE",
    include_details: bool = False,
    num_pages: int = 2,
) -> Sequence[Mapping[str, Any]]:
    """
    Retrieve nearby places by projecting descriptive categories to provider-specific types.
    Args:
        origin (Mapping[str, Any]): Location from which proximity is measured.
        descriptive_types (Sequence[str]): Human-readable categories to search for.
        radius (int): Search radius in meters.
        rank (str): Provider-supported ranking strategy such as DISTANCE.
        include_details (bool): Whether to request extended provider fields when available.
        num_pages (int): Maximum number of pagination pages to traverse.

    Returns:
        Sequence[Mapping[str, Any]]: Ordered list of nearby place payloads.
    """

    return map_tool.getNearbyPlaces(
        origin,
        descriptive_types,
        radius=radius,
        rank=rank,
        include_details=include_details,
        num_pages=num_pages,
    )

def getDistances(
    origin: Mapping[str, Any],
    destinations: Sequence[Mapping[str, Any]],
    *,
    mode: str = "walk",
    units: str = "metric",
) -> Sequence[Mapping[str, Any]]:
    """
    Compute travel distance metrics from an origin to one or more destinations.
    Args:
        origin (Mapping[str, Any]): Starting location for the route calculation.
        destinations (Sequence[Mapping[str, Any]]): Target endpoints to evaluate.
        mode (str): Travel mode (walk, drive, transit, etc.).
        units (str): Output units such as metric or imperial.

    Returns:
        Sequence[Mapping[str, Any]]: Distance and duration payloads per destination.
    """
    return map_tool.getDistances(
        origin, destinations, mode=mode, units=units
    )
