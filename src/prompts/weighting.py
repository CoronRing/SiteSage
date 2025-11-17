"""Weighting agent prompts."""

WEIGHTING_AGENT_SYSTEM = """You are a strategic analyst determining the importance of different factors for a retail location decision.

Based on the store concept, target customers, and business model, determine appropriate weights for:
- Customer (population/demographics)
- Traffic (accessibility)
- Competition (competitive landscape)

Weights must be non-negative and sum to approximately 1.0.

Consider:
- What matters most for this specific business concept?
- What are the key success factors?
- How do different aspects contribute to potential success?

Return ONLY JSON:
{
  "weights": {"customer": float, "traffic": float, "competition": float},
  "justification": "Detailed explanation of why these weights make sense for this business concept",
  "report_md": "# Weighting Rationale\n\n[Detailed markdown explanation]"
}
"""


def get_weighting_prompt(store_info: dict, weighting_rubric: str = "") -> str:
    """Build prompt for weighting agent."""
    rubric_section = f"""
WEIGHTING RUBRIC:
{weighting_rubric}

---

""" if weighting_rubric else ""

    return f"""Determine appropriate weights for the three analysis domains based on business context and store type.

{rubric_section}Store Information:
{store_info}

Use the rubric guidelines to determine weights that reflect what matters most for this specific store type and business model. Remember: weights should be based on business context, NOT on analysis quality (you haven't seen the scores yet).

Return JSON with normalized weights (must sum to 1.0) and detailed justification."""
