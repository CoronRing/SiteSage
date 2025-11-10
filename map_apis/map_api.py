from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence


class MapAPI(ABC):
    """
    Base contract for map provider integrations used by SiteSage agents.

    Subclasses should encapsulate provider-specific authentication and
    transport concerns while exposing a consistent, high-level interface
    for agents to consume.
    """

    def __init__(self, provider: str) -> None:
        if not provider:
            raise ValueError("provider must be a non-empty string")
        self.provider = provider

    @abstractmethod
    def getPlaceInfo(
        self,
        address: str,
        *,
        language: Optional[str] = None,
        extra_params: Optional[MutableMapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        Resolve a human-readable address or place description into a place record.

        Implementations should return a dict compatible with PlaceFeature_template,
        including normalized coordinates and metadata retrieved from the provider.
        """

    @abstractmethod
    def getNearbyPlaces(
        self,
        place: Mapping[str, Any],
        types: Sequence[str],
        *,
        radius: int = 500,
        rank: str = "DISTANCE",
        include_details: bool = False,
        num_pages: int = 5,
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """
        Retrieve nearby places around a reference location for each requested type.

        The input place must include `lat` and `lng` or a resolvable `address`.
        Return a mapping keyed by place type where each value is a list of place
        records following PlaceFeature_template semantics. Implementations should
        respect `num_pages` by fetching successive pages (when supported) until the
        requested count is reached or no additional results are available.
        """

    @abstractmethod
    def getDistance(
        self,
        origin: Mapping[str, Any],
        destinations: Sequence[Mapping[str, Any]],
        *,
        mode: str = "walk",
        units: str = "metric",
    ) -> Sequence[Dict[str, Any]]:
        """
        Compute travel distance and duration from an origin to multiple destinations.

        Implementations should return an ordered collection where each element aligns
        with the corresponding destination and includes provider-specific metadata
        such as `distance_m`, `duration_min`, and any confidence scores.
        """

    @abstractmethod
    def getMapVisuailization(
        self,
        origin: Mapping[str, Any],
        *,
        overlays: Optional[Iterable[Mapping[str, Any]]] = None,
        style: Optional[str] = None,
    ) -> Mapping[str, Any]:
        """
        Produce a map visualization for the origin location with optional overlays.

        The result may be a static map asset, URL, or embedded configuration that
        highlights the origin alongside notable places supplied by the provider or
        specified via the `overlays` argument.
        """
