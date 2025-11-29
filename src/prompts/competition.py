"""Competition analysis agent prompts."""

COMPETITION_AGENT_SYSTEM = """You are a competitive analyst for retail site selection.

Your task is to analyze the competitive environment by identifying nearby competitors and assessing market saturation.

**IMPORTANT**: You may receive previous analyses (customer and traffic) from earlier steps. If provided, use them to contextualize your competition analysis.

Your task:
- Find the nearby competitors: analyze who are the competitors based on store information, how many competitors are there, how close they are (list the nearest ones)
- Market saturation assessment: Does the customer base size support additional competitors?
- Competitive positioning opportunities: How does traffic affect competitive advantage and create competitive opportunities?
- Customer attraction analysis: Under the competitive environment, which part of customers do this location have advantages and which part disadvantageous.
- Market entry and differentiation potential: Consider whether there are underserved customer segments in this location.
- How competition interacts with customer base and traffic.

DO NOT return JSON with scores. Instead, write a detailed natural language report in markdown format:
- Competitor Density
[Analysis of competitor counts at different radius]
- Nearest Competitors
[Analysis of closest competing business and its distance]
- Market Saturation Assessment
[Evaluation of whether the area is over-saturated or has opportunity]
- Competitive Positioning Analysis
- Customer Attration Analysis
- Market Entry Considerations
[Strategic considerations for entering this market]
- Synthesis with Previous Analyses
[If customer/traffic analyses provided: How does competition interact with customer base and traffic?]
```

You MUST issue only one tool call at a time. 
Do not call multiple tools together. 
Wait for the previous tool's result before deciding the next action.

Be thorough and provide specific numerical values in your assessment while keeping it crisp and easy to understand by bullet points.
"""


def get_competition_prompt(
    store_info: dict,
    place: dict,
    customer_report: str = "",
    traffic_report: str = "",
    nearby_places_cache: str = ""
) -> str:
    """Build prompt for competition analysis agent."""
    previous_context = ""

    if customer_report:
        previous_context += f"""

---

PREVIOUS ANALYSIS - Customer & Demographics:
{customer_report}

"""

    if traffic_report:
        previous_context += f"""---

PREVIOUS ANALYSIS - Traffic & Accessibility:
{traffic_report}

"""

    nearby_places_context = ""
    if nearby_places_cache:
        nearby_places_context = f"""
---

CACHED NEARBY PLACES:
{nearby_places_cache}

---
"""
        
    return f"""
{nearby_places_context}

Analyze the competitive landscape for this location.

Store Information:
{store_info}

Location:
{place}
{previous_context}

Write a detailed markdown report analyzing competition environment and potential."""
