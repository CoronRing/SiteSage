from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Tuple

import numpy as np
import rasterio
from rasterio.transform import Affine, rowcol, xy

from worldpop_apis.coordTransform.coordTransform_utils import gcj02_to_wgs84


EARTH_RADIUS_M = 6371008.8  # Mean Earth radius in meters.


@dataclass(frozen=True)
class PopulationStats:
    total_population: float
    age_breakdown: Mapping[str, float]
    age_composition: Mapping[str, float]

class Demographics:
    """Query population rasters around a location."""

    AGE_RASTERS: Mapping[str, str] = {
        "age_0_14": "population_age0_14_shanghai_crop.tif",
        "age_15_59": "population_age15_59_shanghai_crop.tif",
        "age_60_64": "population_age60_64_shanghai_crop.tif",
        "age_65_plus": "population_age65above_shanghai_crop.tif",
        "total": "population_total_pop_shanghai_crop.tif",
    }

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = Path(
            data_dir or Path(__file__).resolve().parents[1] / "data"
        )
        self._layers: MutableMapping[str, np.ndarray] = {}
        self._transform: Optional[Affine] = None
        self._crs = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._nodata: Optional[float] = None
        self._load_layers()

    def _load_layers(self) -> None:
        for layer, filename in self.AGE_RASTERS.items():
            raster_path = self.data_dir / filename
            if not raster_path.exists():
                raise FileNotFoundError(f"Population raster missing: {raster_path}")

            with rasterio.open(raster_path) as src:
                data = src.read(1, masked=True).astype(np.float64)
                self._layers[layer] = np.array(data.filled(np.nan))

                if self._transform is None:
                    self._transform = src.transform
                    self._crs = src.crs
                    self._nodata = src.nodata
                    self._width = src.width
                    self._height = src.height
                else:
                    if src.transform != self._transform:
                        raise ValueError(
                            f"Raster {filename} does not align with existing grid."
                        )

        if self._transform is None:
            raise RuntimeError("No population rasters were loaded.")

    def population_statistics(
        self,
        origin: Tuple[float, float],
        radius_m: float = 500.0,
        coord_ref: str = "GCJ-02",
    ) -> PopulationStats:
        """Return summed population and age composition within the radius.
        Args:
            origin: (lat, lon), the location
            radius_m (float): default 500, the radius to check the statistics.
            coord_ref (str): default GCJ-02, the coordinate reference for AMap and Tencent.
        """
        lat, lon = origin
        lon, lat = self._to_wgs84(lon, lat, coord_ref)
        window = self._compute_window(lat, lon, radius_m)
        if window is None:
            zero_breakdown = {k: 0.0 for k in self._age_layers}
            return PopulationStats(
                total_population=0.0,
                age_breakdown=zero_breakdown,
                age_composition=zero_breakdown,
            )

        mask = self._circle_mask(window, lat, lon, radius_m)
        if not mask.any():
            zero_breakdown = {k: 0.0 for k in self._age_layers}
            return PopulationStats(
                total_population=0.0,
                age_breakdown=zero_breakdown,
                age_composition=zero_breakdown,
            )

        sums: Dict[str, float] = {}
        for layer, data in self._layers.items():
            sub_array = data[window.row_slice, window.col_slice]
            masked = np.where(mask, sub_array, 0.0)
            sums[layer] = float(np.nansum(masked))

        age_breakdown = {k: v for k, v in sums.items() if k != "total"}
        total_population = sums.get("total", sum(age_breakdown.values()))
        composition = self._composition(age_breakdown, total_population)

        return PopulationStats(
            total_population=total_population,
            age_breakdown=age_breakdown,
            age_composition=composition,
        )

    def _composition(
        self, breakdown: Mapping[str, float], total_population: float
    ) -> Dict[str, float]:
        if total_population <= 0:
            return {k: 0.0 for k in breakdown}
        return {k: v / total_population for k, v in breakdown.items()}

    @property
    def _age_layers(self) -> Iterable[str]:
        return [k for k in self._layers.keys() if k != "total"]

    def _to_wgs84(self, lon: float, lat: float, coord_ref: str) -> Tuple[float, float]:
        ref = (coord_ref or "GCJ-02").upper()
        if ref == "GCJ-02":
            converted_lon, converted_lat = gcj02_to_wgs84(lon, lat)
            return float(converted_lon), float(converted_lat)
        if ref == "WGS84":
            return lon, lat
        raise ValueError(f"Unsupported coordinate reference: {coord_ref}")

    def _compute_window(
        self, lat: float, lon: float, radius_m: float
    ) -> Optional["Window"]:
        if (
            self._transform is None
            or self._width is None
            or self._height is None
        ):
            return None

        lat_delta = radius_m / 111_320.0
        cos_lat = math.cos(math.radians(lat))
        lon_denominator = max(1e-12, 111_320.0 * cos_lat)
        lon_delta = radius_m / lon_denominator

        min_lat = lat - lat_delta
        max_lat = lat + lat_delta
        min_lon = lon - lon_delta
        max_lon = lon + lon_delta

        rows = []
        cols = []
        for corner_lon in (min_lon, max_lon):
            for corner_lat in (min_lat, max_lat):
                row, col = rowcol(self._transform, corner_lon, corner_lat)
                rows.append(row)
                cols.append(col)

        row_min = max(0, min(rows))
        row_max = min(self._height, max(rows) + 1)
        col_min = max(0, min(cols))
        col_max = min(self._width, max(cols) + 1)

        if row_min >= row_max or col_min >= col_max:
            return None

        return Window(slice(row_min, row_max), slice(col_min, col_max))

    def _circle_mask(
        self, window: "Window", center_lat: float, center_lon: float, radius_m: float
    ) -> np.ndarray:
        rows = np.arange(window.row_slice.start, window.row_slice.stop)
        cols = np.arange(window.col_slice.start, window.col_slice.stop)
        row_grid, col_grid = np.meshgrid(rows, cols, indexing="ij")
        flat_rows = row_grid.ravel()
        flat_cols = col_grid.ravel()
        lon_flat, lat_flat = xy(
            self._transform, flat_rows, flat_cols, offset="center"
        )
        lon_grid = np.reshape(np.asarray(lon_flat), row_grid.shape)
        lat_grid = np.reshape(np.asarray(lat_flat), row_grid.shape)
        distances = _haversine_distance(
            np.radians(lat_grid),
            np.radians(lon_grid),
            math.radians(center_lat),
            math.radians(center_lon),
        )
        return distances <= radius_m


@dataclass(frozen=True)
class Window:
    row_slice: slice
    col_slice: slice


def _haversine_distance(
    lat_rad: np.ndarray,
    lon_rad: np.ndarray,
    center_lat_rad: float,
    center_lon_rad: float,
) -> np.ndarray:
    lat_diff = lat_rad - center_lat_rad
    lon_diff = lon_rad - center_lon_rad
    sin_lat = np.sin(lat_diff / 2.0)
    sin_lon = np.sin(lon_diff / 2.0)
    a = sin_lat**2 + np.cos(center_lat_rad) * np.cos(lat_rad) * sin_lon**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return EARTH_RADIUS_M * c


__all__ = ["Demographics", "PopulationStats"]
