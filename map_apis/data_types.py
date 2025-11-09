# descriptor
LocationIntakeRequest_template = \
"""{
  "location_id": "string",
  "address": "string",
  "lat": 31.2304,
  "lng": 121.4737,
  "category": "electronics_retail",
  "subcategory": "multi_brand",
  "size_sqm": 250,
  "price_tier": "mid",
  "brand": "Optional<string>",
  "hours": "Optional<string>",
  "notes": "Optional<string>"
}"""

PlaceFeature_template = \
"""{
  "provider": "baidu|amap|osm|other",
  "place_id": "string",
  "name": "string",
  "category": "string",
  "subcategory": "string",
  "lat": 31.23,
  "lng": 121.47,
  "rating": 4.3,
  "review_count": 210,
  "price_level": "Optional<int>",
  "open_hours": "Optional<string>",
  "mall_id": "Optional<string>",
  "floor": "Optional<string>",
  "tags": ["electronics", "phone", "repair"],
  "last_seen": "ISO-8601"
}"""

Catchment_template = \
"""{
  "mode": "walk|drive|transit",
  "minutes": 5,
  "polygon_geojson": { "type": "Polygon", "coordinates": [...] },
  "population_residential": 12000,
  "population_daytime_proxy": 9000,
  "coverage_score": 0.82,
  "provenance": ["provider:amap:isochrone:2025-10-15"]
}"""

Competitor_template = \
"""{
  "place": PlaceFeature,
  "distance_m": 540,
  "transit_time_min": 8,
  "attractiveness_score": 0.67,
  "est_revenue_range": { "low": 2_000_000, "high": 6_000_000, "currency": "CNY" },
  "uncertainty": 0.35,
  "drivers": ["brand_strength", "mall_anchor", "reviews"],
  "provenance": [...]
}"""

AccessibilityScore_template = \
"""{
  "transit_distance_m": 110,
  "walk_connectivity_proxy": 0.74,
  "corner_flag": true,
  "frontage_proxy": 0.6,
  "visibility_proxy": 0.7,
  "parking_proxy": 0.5,
  "delivery_access_proxy": 0.8,
  "alignment_score": 0.71,
  "notes": "Near Line 2 exit; mid-block visibility limited by trees",
  "provenance": [...]
}"""

