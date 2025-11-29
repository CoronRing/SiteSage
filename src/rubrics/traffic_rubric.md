# **Traffic & Accessibility Potential Rubric (Location-Oriented)**

Score **0–10** based on how easily and naturally target customers reach and pass the site.

### Weights (sum = 100%)

1. Public Transit & Connectivity Quality – **35%**
2. Walkability, Parking & Road Access – **25%**
3. Target Customer Mobility Fit – **20%**
4. Traffic Volume & Temporal Benefits – **20%**

---

1. Public Transit & Connectivity Quality (35%)

Consider **number of modes**, **distance**, **integration**, and **passenger volumes**, **relative to the city**.

### Excellent (9–10)

- Node is among the **top ~10–15%** in the city for relevant transit passenger volumes.
- Multiple **high‑frequency transit modes**, typically including:
  - 2+ metro/subway lines or an equivalent (e.g., metro + major BRT + dense bus hub), and
  - Short, convenient connections between modes.
- Nearest key transit access typically **≤300 m** (≤5 min walk); ideally the project is **inside or directly connected to** the station/hub.
- As a rough guideline in large cities:
  - Daily passenger volumes ~**150k–250k** → **9.0–9.4**,
  - **>250k/day** and/or central CBD/interchange role → **9.5–10.0**.

### Good (7–8.5)

- Strong transit access but not a top‑decile city node:
  - At least one major metro line or a well‑used suburban rail/BRT line, and/or
  - Dense bus network with frequent service.
- Typical walk distances **≤500 m** from main stops/stations.
- Passenger volumes clearly above average for the city but below its largest interchanges.

### Adequate (5–6.9)

- Basic transit coverage:
  - One line or a few bus routes within 500–800 m.
- Gaps in service hours or frequency; some segments of target customers face mild inconvenience.

### Poor (3–4.9)

- Sparse transit:
  - Infrequent buses; no rail within easy walking distance.
- Many potential customers must rely on long walks, transfers, or private vehicles.

### Insufficient (0–2.9)

- Minimal or no effective transit access for the majority of target customers.

---

## 2. Walkability, Parking & Road Access (25%)

Evaluate **pedestrian experience**, **car access**, and **overall ease of approach**.

### Excellent (9–10)

- Safe, continuous sidewalks and **natural pedestrian paths** that pass the site frontage.
- Multiple **entry points** and barrier‑free access (ramps, elevators where needed).
- Sufficient, reasonably priced parking **≤3–5 min walk** (on‑site or adjacent), or strong drop‑off points.
- Simple, well‑signed road network; vehicles can approach and exit without major congestion.

### Good (7–8)

- Generally walkable environment; minor issues (e.g., some crossings or narrow sidewalks).
- Adequate parking within 5–8 minutes’ walk or clear drop‑off space.
- Road access workable with occasional congestion.

### Adequate (5–6)

- Mixed conditions:
  - Walkways may be indirect or fragmented.
  - Limited or more distant parking; some navigation complexity for drivers.

### Poor (3–4)

- Difficult for pedestrians (broken sidewalks, dangerous crossings) **or**
- Very limited/expensive parking and tricky vehicle access; approach is a clear deterrent.

### Insufficient (0–2)

- Significant **physical or regulatory barriers** (e.g., no pedestrian infrastructure, restricted vehicle access) that severely limit reachability for most customers.

---

## 3. Target Customer Mobility Fit (20%)

How well the site’s access modes match **how target customers actually travel**.

### Excellent (9–10)

- Dominant customer travel modes are **directly supported**:
  - E.g., students heavily reliant on metro next door; families with cars served by abundant nearby parking.
- Minimal extra detour time:
  - For most target users, added walk/drive time ≤3 minutes vs their natural path.

### Good (7–8)

- Mostly aligned with some gaps:
  - E.g., office workers well‑served by transit, but residents less so.
- Typical detour ≤5 minutes for key segments.

### Adequate (5–6)

- Partial alignment:
  - Some important segments must make moderate detours, but others are well served.

### Poor (3–4)

- Main customer segments face material frictions:
  - Long detours, no parking despite car dependence, or poor transit despite student dependence.

### Insufficient (0–2)

- Accessibility patterns are **mismatched** with how target customers move; even interested customers find it hard to visit regularly.

---

## 4. Traffic Volume & Temporal Benefits (20%)

Assess **magnitude and continuity of flows** around the actual site, not just the wider node.

### Excellent (9–10)

- The storefront is directly on or immediately adjacent to **primary pedestrian flows**:
  - Large mall corridors, station exits, main street sidewalks.
- Strong and predictable peaks (e.g., commute, lunch, after‑school, evenings/weekends) with **visible, sustained streams**.
- For transaction‑driven formats, realistic potential for **above‑average** pass‑by volumes given the micro‑location.

### Good (7–8)

- Solid traffic:
  - Visible foot or vehicle traffic most of the day.
- Storefront is near but not perfectly on the main flow, or traffic is strong only in certain periods (e.g., evenings/weekends).

### Adequate (5–6)

- Moderate, usable traffic:
  - People pass but flows are thinner, or the store is off the main corridor and relies partly on intentional visits.

### Poor (3–4)

- Limited passing traffic:
  - Side street, upper floor with weak draw, or deeply inside a complex without clear wayfinding.

### Insufficient (0–2)

- Very low visible traffic near the site; customers must almost exclusively be destination‑driven.

---

### Traffic & Accessibility – Output Format

```json
{
  "score": 9.0,
  "justification": "The site is directly integrated with a multi-line metro interchange and dense bus network, with strong all-day pedestrian flows passing the storefront. Short walking distances, good sidewalks, and ample nearby parking create excellent accessibility aligned with commuter and office-worker mobility patterns."
}
```
