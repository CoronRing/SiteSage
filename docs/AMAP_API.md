# AMap API Reference

## Overview
- Base URL: `https://restapi.amap.com`
- Authentication: append `key=<YOUR_AMAP_API_KEY>` to every request.
- Format: JSON responses by default (`output=JSON`); status `1` indicates success.

## Geocoding (`/v3/geocode/geo`)
- Purpose: Convert a street address into latitude/longitude and metadata.
- Required params: `address`, `key`.
- Optional params: `city` (city name/adcode to disambiguate), `batch` (`true|false`, defaults false), `extensions=all` for richer metadata, `language` (`zh_cn|en`).
- Sample request: `GET /v3/geocode/geo?address=上海市徐汇区衡山路&extensions=all&key=...`
- Response outline:
  - `geocodes[].formatted_address`, `province`, `city`, `district`.
  - `geocodes[].location` (`lng,lat`), `adcode`, `level` (administrative precision), `type`.
  - When `extensions=all`, additional `neighborhood`, `building`, and `streetNumber` structures are populated.

## Nearby Place Search (`/v5/place/around`)
- Purpose: Fetch points of interest around a reference coordinate.
- Required params: `location=<lng>,<lat>`, `key`.
- Optional params: `radius` (meters; 1–50000, defaults 1000), `types` (pipe-delimited AMap type codes, max 20), `sortrule=distance|weight`, `page_size` (1–25), `page_index` (1–100), `keywords` (UTF-8, ≤45 chars), `show_fields` (e.g., `photos,basic,children`).
- Response outline:
  - `pois[].id`, `name`, `typecode` (6-digit POI category, hierarchically structured).
  - `pois[].type` (semicolon-separated textual categories), `location` (`lng,lat`), `address`, `tel`.
  - Optional metrics: `distance` (meters), `rating`, `cost`, `biz_ext` (business extensions), `photos` (array of `title`/`url`).
- Type codes: six-character strings where the first two digits indicate the macro category (e.g., `01`—financial services), third and fourth digits the middle category, and last two digits the sub-category. Full tables are provided in the official AMap POI type reference; ensure submitted codes match this taxonomy to avoid empty results.

## Distance Matrix (`/v3/distance`)
- Purpose: Compute travel distance and duration from one origin to one or more destinations.
- Required params: `origins=<lng>,<lat>` (supports multiple origins), `destination=<lng>,<lat>`, `key`.
- Optional params: `type` (`0` driving, `1` transit, `2` cycling, `3` walking), `output`. Each request supports up to 100 origin-destination pairs.
- Response fields: `results[].distance` (meters), `results[].duration` (seconds), `results[].info` (status message per pair), `results[].origins_id` when batch origins supplied.
- Note: Batch distance requires semicolon-separated origin coordinates.

## Static Map Visualization (`/v3/staticmap`)
- Purpose: Generate a static image highlighting key locations.
- Required params: `location=<lng>,<lat>`, `key`.
- Optional params: `zoom` (1–17), `size=width*height` (max 1024*1024), `scale=1|2`, `markers` (≤50 markers, pipe-delimited e.g., `mid,,A:lng,lat`), `paths` (≤10 path definitions), `styles`.
- Response: Binary PNG/JPEG image; when building URLs programmatically ensure you preserve encoding for marker strings.

## Error Handling
- `status` of `0` or HTTP 4xx/5xx indicates failure; inspect `info` and `infocode`.
- Common errors: `INVALID_USER_KEY` (key mismatch), `SERVICE_NOT_AVAILABLE` (temporary outage), `USER_DAILY_QUERY_OVER_LIMIT` (quota exceeded).
- Implement retries with exponential backoff for transient network failures; do not retry quota or auth errors without manual intervention.

## Usage Tips
- Keep API keys outside version control; inject via `AMAP_API_KEY` or similar environment variables.
- Cache frequent geocoding/place queries to avoid hitting rate limits.
- Type codes are hierarchical (e.g., `050000` for food & beverage); combine with business logic before calling the nearby search endpoint.
- When visualizing overlays, limit marker count to avoid exceeding URL length; consider hosting the generated static map URL alongside query parameters for auditability.

## References
- AMap Web Service APIs Overview (高德开放平台 Web 服务 API 总览). (API ref)[https://lbs.amap.com/api]
- AMap POI 分类编码表 for official POI type codes and descriptions.
- AMap Static Map Service (Web 服务 API 静态地图) for marker/path syntax and size constraints.
