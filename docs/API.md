# SiteSage API Reference

## Overview

SiteSage provides a REST API for running site selection analyses. The frontend server exposes endpoints for analysis execution and artifact retrieval.

---

## Base URL

```
http://127.0.0.1:8000
```

---

## Endpoints

### 1. Run Analysis

**Endpoint:** `POST /api/run`

**Description:** Executes the full SiteSage analysis pipeline for a given business prompt.

**Request Body (JSON):**

```json
{
  "session_id": "optional_custom_session_id",
  "prompt": "Your business location prompt",
  "language": "en"
}
```

**Parameters:**

| Parameter  | Type   | Required | Default                  | Description                                                       |
| ---------- | ------ | -------- | ------------------------ | ----------------------------------------------------------------- |
| session_id | string | No       | Auto-generated timestamp | Unique identifier for this analysis session                       |
| prompt     | string | Yes      | -                        | Natural language description of the business concept and location |
| language   | string | No       | "en"                     | Language for analysis ("en" or "zh")                              |

**Response (JSON):**

See [Response Schema](#response-schema) below.

**Example Request (cURL):**

```bash
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Open a boutique coffee shop targeting young professionals near Times Square, New York",
    "language": "en"
  }'
```

**Example Request (Python):**

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/run",
    json={
        "prompt": "Open a boutique coffee shop targeting young professionals near Times Square, New York",
        "language": "en"
    }
)

result = response.json()
print(f"Final Score: {result['final_score']}")
print(f"Report: {result['final_report']['report_path']}")
```

**Example Request (JavaScript):**

```javascript
fetch("http://127.0.0.1:8000/api/run", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    prompt:
      "Open a boutique coffee shop targeting young professionals near Times Square, New York",
    language: "en",
  }),
})
  .then((res) => res.json())
  .then((data) => {
    console.log("Final Score:", data.final_score);
    console.log("Report:", data.final_report.report_path);
  });
```

---

### 2. Health Check

**Endpoint:** `GET /healthz`

**Description:** Simple liveness check.

**Response:**

```
OK
```

---

### 3. Frontend UI

**Endpoint:** `GET /`

**Description:** Serves the interactive web interface.

**Response:** HTML page (golden/royal theme UI)

---

### 4. Static Files (Artifacts)

**Endpoint:** `GET /save/{session_id}/{filename}`

**Description:** Retrieves generated reports and artifacts.

**Example:**

```
GET /save/sess_20250111_123456/07_final_report.md
```

---

## Response Schema

### Complete Response Structure

```json
{
  "session_id": "sess_20250111_123456",
  "input": {
    "prompt": "Your original prompt",
    "language": "en"
  },
  "store_info": {
    "store_type": "Coffee Shop",
    "business_description": "Boutique coffee shop with cozy atmosphere",
    "service_mode": "Dine-in + Takeaway",
    "target_customers": ["Young Professionals", "Students"],
    "price_level": "Mid-range",
    "time_window": "Morning peak",
    "location_query": "Times Square, New York"
  },
  "place": {
    "name": "Times Square",
    "lat": 40.758896,
    "lng": -73.98513,
    "lon": -73.98513,
    "formatted_address": "Manhattan, NY 10036, USA"
  },
  "features": {
    "customer": {
      "radius_m": 500,
      "population_total": 12500,
      "age_buckets": {
        "0-14": 850,
        "15-24": 2200,
        "25-64": 8100,
        "65+": 1350
      },
      "notes": "Dense urban population with high proportion of working-age adults"
    },
    "traffic": {
      "nearby_counts": {
        "subway_station": 3,
        "bus_stop": 8,
        "parking": 2
      },
      "distances": {
        "nearest_subway": 120,
        "nearest_bus": 45,
        "nearest_parking": 200
      },
      "nearest_transit": {
        "name": "Times Square-42nd St Station",
        "type": "subway_station",
        "distance": 120
      },
      "notes": "Excellent public transit accessibility"
    },
    "competition": {
      "competitor_counts": {
        "coffee_shop": 15,
        "cafe": 12,
        "restaurant": 45
      },
      "nearest_competitor": {
        "name": "Starbucks Times Square",
        "type": "coffee_shop",
        "distance": 85
      },
      "notes": "High competition but indicates proven demand"
    }
  },
  "scores": {
    "customer": 8.5,
    "traffic": 9.0,
    "competition": 6.5
  },
  "weights": {
    "customer": 0.35,
    "traffic": 0.3,
    "competition": 0.35,
    "justification": "Balanced weighting with emphasis on customer base and competition analysis"
  },
  "final_score": 7.95,
  "final_report": {
    "title": "Site Selection Analysis: Boutique Coffee Shop - Times Square, NYC",
    "recommendation": "RECOMMENDED with considerations",
    "highlights": [
      "Excellent transit accessibility (Score: 9.0)",
      "Strong customer demographics (Score: 8.5)",
      "High competition requires differentiation (Score: 6.5)"
    ],
    "report_path": "/save/sess_20250111_123456/07_final_report.md"
  },
  "assets": {
    "reports": {
      "understanding": "/save/sess_20250111_123456/01_understanding.md",
      "customer": "/save/sess_20250111_123456/02_customer.md",
      "traffic": "/save/sess_20250111_123456/03_traffic.md",
      "competition": "/save/sess_20250111_123456/04_competition.md",
      "weighting": "/save/sess_20250111_123456/05_weighting.md",
      "evaluation": "/save/sess_20250111_123456/06_evaluation.md",
      "final": "/save/sess_20250111_123456/07_final_report.md"
    },
    "map_image_url": "/save/sess_20250111_123456/static_map.png"
  },
  "errors": [],
  "timestamps": {
    "started_at": "2025-01-11T12:34:56.789Z",
    "ended_at": "2025-01-11T12:35:42.123Z"
  }
}
```

### Field Descriptions

#### Top-Level Fields

| Field        | Type   | Description                                             |
| ------------ | ------ | ------------------------------------------------------- |
| session_id   | string | Unique identifier for this analysis run                 |
| input        | object | Original request parameters                             |
| store_info   | object | Extracted business concept details                      |
| place        | object | Geocoded location information                           |
| features     | object | Analyzed site features (customer, traffic, competition) |
| scores       | object | Evaluation scores (0-10 scale) for each domain          |
| weights      | object | Domain importance weights (sum to 1.0)                  |
| final_score  | float  | Weighted overall score (0-10 scale)                     |
| final_report | object | Executive summary and recommendations                   |
| assets       | object | Paths to generated artifacts                            |
| errors       | array  | List of errors encountered (empty if successful)        |
| timestamps   | object | Analysis start and end times (ISO-8601)                 |

#### Scoring

- **Domain Scores** (customer, traffic, competition): 0-10 scale

  - Evaluated by specialized agents using detailed rubrics
  - 0-3: Poor, significant issues
  - 4-6: Fair, mixed factors
  - 7-8: Good, generally favorable
  - 9-10: Excellent, highly favorable

- **Weights**: Decimal values (0.0-1.0) that sum to 1.0

  - Determined by business context (not analysis quality)
  - Example: {customer: 0.35, traffic: 0.30, competition: 0.35}

- **Final Score**: Weighted sum
  - Formula: `(customer_score × w_customer) + (traffic_score × w_traffic) + (competition_score × w_competition)`
  - Range: 0-10
  - Interpretation similar to domain scores

---

## Error Handling

### HTTP Status Codes

| Code | Description                                     |
| ---- | ----------------------------------------------- |
| 200  | Success                                         |
| 400  | Bad Request (invalid input)                     |
| 500  | Internal Server Error (analysis pipeline error) |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Common Errors

1. **Missing Required Fields**

   ```json
   {
     "detail": "Field 'prompt' is required"
   }
   ```

2. **Invalid Language**

   ```json
   {
     "detail": "Language must be 'en' or 'zh'"
   }
   ```

3. **API Key Not Set**

   - Returns 500 with error message in `errors` array
   - Check environment variables

4. **Geocoding Failed**
   - Returns 200 with partial data
   - Check `errors` array for details

---

## Rate Limiting

- No explicit rate limiting currently implemented
- Be mindful of:
  - OpenAI API rate limits
  - Google Maps/AMap API quotas
  - Server resource constraints

---

## Best Practices

1. **Session IDs**

   - Use descriptive session IDs for easier artifact management
   - Format: `{project}_{location}_{timestamp}`

2. **Prompts**

   - Be specific about business concept
   - Include target customer demographics
   - Specify location clearly (address or landmark)
   - Mention key requirements (e.g., "morning traffic", "parking access")

3. **Error Handling**

   - Always check the `errors` array in responses
   - Implement retry logic for transient failures
   - Log session IDs for debugging

4. **Artifact Access**
   - Reports are available immediately after analysis
   - Artifacts persist in `src/save/{session_id}/`
   - Access via `/save/{session_id}/{filename}`

---

## Programming Language Examples

### Python with Requests

```python
import requests
import json

def analyze_location(prompt: str, language: str = "en"):
    response = requests.post(
        "http://127.0.0.1:8000/api/run",
        json={"prompt": prompt, "language": language}
    )
    response.raise_for_status()
    return response.json()

# Usage
result = analyze_location(
    "Coffee shop near Central Park, targeting morning runners"
)
print(f"Score: {result['final_score']:.2f}")
for highlight in result['final_report']['highlights']:
    print(f"- {highlight}")
```

### JavaScript/Node.js with Fetch

```javascript
async function analyzeLocation(prompt, language = "en") {
  const response = await fetch("http://127.0.0.1:8000/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, language }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Usage
analyzeLocation(
  "Coffee shop near Central Park, targeting morning runners"
).then((result) => {
  console.log(`Score: ${result.final_score.toFixed(2)}`);
  result.final_report.highlights.forEach((h) => console.log(`- ${h}`));
});
```

### cURL

```bash
# Basic request
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Coffee shop near Central Park", "language": "en"}'

# Save response to file
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Coffee shop near Central Park", "language": "en"}' \
  -o result.json

# Pretty print with jq
curl -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Coffee shop near Central Park", "language": "en"}' \
  | jq '.'
```

---

## See Also

- [DESIGN.md](DESIGN.md) - System architecture and design patterns
- [INSTALLATION.md](INSTALLATION.md) - Setup and configuration guide
- [../README.md](../README.md) - Project overview and quick start
