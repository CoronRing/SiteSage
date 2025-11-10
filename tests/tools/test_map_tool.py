from __future__ import annotations

import os
from pathlib import Path

import pytest
import sys
sys.path.append("../../")
from tools.map import MapTool


def _load_dotenv() -> None:
    """Populate os.environ using the project-level .env if present."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@pytest.mark.integration
def test_map_tool_end_to_end() -> None:
    _load_dotenv()
    if not os.getenv("AMAP_API_KEY"):
        pytest.skip("AMAP_API_KEY missing; cannot hit live AMap services.")

    tool = MapTool()
    anchor = tool.getPlaceInfo("Shanghai Tower")
    print(anchor)

    assert anchor["provider"] == "amap"
    assert anchor["lat"] and anchor["lng"]

    viz = tool.getMapVisualization(anchor, overlays=[{"label": "Origin", "lat": anchor["lat"], "lng": anchor["lng"]}])
    print(viz)
    assert viz["provider"] == "amap"
    assert "http" in viz["url"]

    nearby = tool.getNearbyPlaces(anchor, ["Coffee House"], radius=1000, num_pages=1)
    print(nearby)
    assert isinstance(nearby, list)
    assert nearby, "Expected at least one coffee house near Shanghai Tower."

    target = nearby[0]
    assert target["lat"] and target["lng"]

    distances = tool.getDistances(anchor, [target], mode="drive")
    print(distances)
    assert distances and distances[0]["destination"] == target

if __name__ == "__main__":
    test_map_tool_end_to_end()