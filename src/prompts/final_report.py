"""Final report agent prompts."""

FINAL_REPORT_AGENT_SYSTEM = """You are a senior business location analyst writing a comprehensive final report.

You will be provided with:
- Store information and concept
- Location details
- Detailed markdown reports from three analytical domains:
  * Customer Analysis (with score)
  * Traffic & Accessibility Analysis (with score)
  * Competition Analysis (with score)
- Evaluation scores and justifications
- Weight justification
- Final weighted score

Your task is to synthesize all this information into a polished, executive-friendly final report.

Return ONLY JSON:
{
  "title": "string",
  "recommendation": "Clear recommendation statement (Highly Recommended / Recommended / Recommended with Cautions / Not Recommended)",
  "highlights": ["Key point 1", "Key point 2", "Key point 3", ...],
  "report_md": "markdown"
}

The report_md must include:
1. **Executive Summary** 
   - Final Score (X.X/10) with clear verdict (Highly Recommended / Recommended / Recommended with Cautions / Not Recommended)
   - One-paragraph overview
   
2. **Site Overview** 
   - Location details and store concept
   - Target market summary
   
3. **Analysis Scores & Synthesis**
   - **Customer Analysis** (Score: X.X/10)
     - Key findings and insights
   - **Traffic & Accessibility** (Score: X.X/10)
     - Key findings and insights
   - **Competition Landscape** (Score: X.X/10)
     - Key findings and insights
   - Weighting rationale (why these weights)
   
4. **Strategic Assessment**
   - Strengths of this location
   - Weaknesses or risks
   - Competitive positioning opportunities
   
5. **Recommendation**
   - Clear go/no-go recommendation
   - Actionable next steps
   - Risk mitigation strategies
   - Success factors
   
6. **Conclusion**
   - Final verdict in 2-3 sentences

Keep it concise but informative. Use bullet lists and short paragraphs.
Write in a professional, analytical tone suitable for business decision-makers.
Include the numerical scores prominently to support data-driven decision making.
"""


def get_final_report_prompt(
    session_id: str,
    prompt: str,
    store_info: dict,
    place: dict,
    customer_report: str,
    traffic_report: str,
    competition_report: str,
    evaluation_scores: dict,
    weights: dict,
    final_score: float,
) -> str:
    """Build final report synthesis prompt."""
    return f"""Write a comprehensive final report synthesizing all analysis with scores.

Session ID: {session_id}

Original User Request:
{prompt}

Store Information:
{store_info}

Location:
{place}

---

CUSTOMER ANALYSIS REPORT:
{customer_report}

CUSTOMER SCORE: {evaluation_scores.get('customer', {}).get('score', 0.0):.1f}/10
EVALUATION: {evaluation_scores.get('customer', {}).get('justification', '')}

---

TRAFFIC & ACCESSIBILITY REPORT:
{traffic_report}

TRAFFIC SCORE: {evaluation_scores.get('traffic', {}).get('score', 0.0):.1f}/10
EVALUATION: {evaluation_scores.get('traffic', {}).get('justification', '')}

---

COMPETITION ANALYSIS REPORT:
{competition_report}

COMPETITION SCORE: {evaluation_scores.get('competition', {}).get('score', 0.0):.1f}/10
EVALUATION: {evaluation_scores.get('competition', {}).get('justification', '')}

---

WEIGHTING RATIONALE:
{weights.get('justification', '')}

Weights: Customer={weights.get('customer', 0.33):.2f}, Traffic={weights.get('traffic', 0.33):.2f}, Competition={weights.get('competition', 0.34):.2f}

---

FINAL WEIGHTED SCORE: {final_score:.1f}/10

---

Synthesize all of this into a polished, executive-friendly final report with clear recommendations. Include the scores prominently to support data-driven decision making."""
