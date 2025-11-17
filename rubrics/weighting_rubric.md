# Weighting Rubric

## Purpose

This rubric guides the determination of relative importance (weights) for the three analysis domains: **Customer**, **Traffic & Accessibility**, and **Competition**. Weights should be based on **business context and store type**, not on the quality of the analysis itself.

---

## Guiding Principles

1. **Business-Context Driven**: Weights reflect what matters most for the specific store type and business model
2. **Store-Type Consistency**: Similar store types should have similar weight distributions
3. **Independence from Analysis Quality**: Weights are determined BEFORE seeing analysis scores to avoid bias
4. **Must Sum to 1.0**: Ensure weights add up to 100% (customer + traffic + competition = 1.0)

---

## Weight Determination Factors

### Customer Analysis Weight (Typical Range: 0.25 - 0.40)

**Consider Higher Weight (0.35-0.40) when:**
- Store targets specific demographic segments (age, income, lifestyle)
- Product/service is highly specialized or niche
- Customer base density is critical for viability
- Repeat customer behavior is essential for success
- Examples: Boutique stores, specialty services, membership-based businesses

**Consider Moderate Weight (0.30-0.35) when:**
- Store serves general population with some targeting
- Balanced between niche and mass market
- Customer demographics matter but aren't the only factor
- Examples: Coffee shops, casual dining, retail chains

**Consider Lower Weight (0.25-0.30) when:**
- Store serves very broad demographic
- Location convenience matters more than customer profile
- Product is commodity-like with minimal targeting
- Examples: Convenience stores, fast food, gas stations

---

### Traffic & Accessibility Weight (Typical Range: 0.30 - 0.45)

**Consider Higher Weight (0.40-0.45) when:**
- Business model relies on foot traffic or impulse purchases
- Public transit access is critical for target customers
- Parking availability is a major consideration
- High customer visit frequency expected
- Examples: Coffee shops (especially commuter-focused), convenience stores, quick-service restaurants

**Consider Moderate Weight (0.33-0.38) when:**
- Mix of destination visits and foot traffic
- Some customers plan visits, others are opportunistic
- Multiple transportation modes important
- Examples: Casual dining, retail boutiques, service businesses

**Consider Lower Weight (0.30-0.33) when:**
- Destination business where customers specifically seek it out
- Online presence or delivery reduces need for physical access
- Customers typically drive or use transportation apps
- Examples: Fine dining, specialty stores, appointment-based services

---

### Competition Analysis Weight (Typical Range: 0.25 - 0.40)

**Consider Higher Weight (0.35-0.40) when:**
- Market is saturated or highly competitive
- Differentiation is challenging but critical
- Customer switching costs are low
- Price competition is significant
- Examples: Coffee shops in urban areas, fast food, commodity retail

**Consider Moderate Weight (0.30-0.35) when:**
- Moderate competition with room for differentiation
- Mix of direct and indirect competitors
- Some customer loyalty expected
- Examples: Casual dining, specialty retail, most service businesses

**Consider Lower Weight (0.25-0.30) when:**
- Unique or highly differentiated offering
- Limited direct competition
- Strong brand or customer loyalty expected
- Barriers to entry protect position
- Examples: Luxury goods, unique concepts, franchise exclusivity zones

---

## Store Type Guidelines

### Coffee Shop / Café
**Recommended Weights:**
- Customer: 0.30-0.33 (important but not dominant)
- Traffic: 0.35-0.40 (critical for foot traffic and commuter access)
- Competition: 0.30-0.35 (saturated market in urban areas)

**Justification:** Coffee shops rely heavily on convenient access for daily commuters and foot traffic. Competition is significant in urban areas. Customer demographics matter but are less critical than location and accessibility.

---

### Quick-Service Restaurant (QSR)
**Recommended Weights:**
- Customer: 0.25-0.30 (broad demographic appeal)
- Traffic: 0.40-0.45 (critical for impulse purchases and convenience)
- Competition: 0.30-0.35 (moderate to high competition)

**Justification:** QSRs depend on high traffic volume and convenience. Broad demographic appeal reduces emphasis on customer analysis.

---

### Boutique / Specialty Retail
**Recommended Weights:**
- Customer: 0.35-0.40 (niche targeting essential)
- Traffic: 0.30-0.35 (destination shopping, but some foot traffic helps)
- Competition: 0.25-0.30 (differentiation through uniqueness)

**Justification:** Specialty retail depends on finding the right customer base. Less reliant on convenience as customers seek out unique offerings.

---

### Casual Dining Restaurant
**Recommended Weights:**
- Customer: 0.32-0.35 (balanced demographic targeting)
- Traffic: 0.33-0.37 (mix of destination and convenience)
- Competition: 0.30-0.35 (moderate competition)

**Justification:** Balanced approach as casual dining is both destination and opportunistic, requires demographic fit, and faces moderate competition.

---

### Convenience Store
**Recommended Weights:**
- Customer: 0.25-0.28 (serves broad population)
- Traffic: 0.42-0.47 (critical for impulse and convenience purchases)
- Competition: 0.28-0.33 (location matters more than differentiation)

**Justification:** Convenience stores are all about location and accessibility. Customer demographics less critical as they serve general population.

---

## Output Format

Return JSON with normalized weights and clear justification:

```json
{
  "weights": {
    "customer": 0.33,
    "traffic": 0.37,
    "competition": 0.30
  },
  "justification": "For a coffee shop targeting young professionals and students, traffic/accessibility receives the highest weight (0.37) due to the importance of commuter access and foot traffic for daily visits. Customer analysis is weighted at 0.33 as demographic targeting is important but secondary to convenient location. Competition receives 0.30 given the saturated coffee shop market in urban areas where differentiation through quality and service is key.",
  "store_type": "Coffee Shop / Café",
  "business_model": "Commuter-focused with morning traffic emphasis",
  "report_md": "# Weighting Analysis\n\n[Full markdown report explaining the weight determination...]"
}
```

---

## Quality Standards

**Excellent Weight Determination (Would warrant high evaluation):**
- Clear alignment between store type and weight distribution
- Thorough justification referencing business model specifics
- Consideration of target customers, location context, and competitive landscape
- Proper normalization (sums to 1.0)
- Specific reasoning, not generic statements

**Adequate Weight Determination:**
- Reasonable weight distribution for store type
- Basic justification provided
- Weights sum to 1.0
- General reasoning that makes sense

**Poor Weight Determination:**
- Weights don't match store type characteristics
- Weak or missing justification
- Equal weights (0.33, 0.33, 0.34) without clear reasoning
- Doesn't consider business model specifics

---

## Important Notes

1. **No Access to Scores**: Weights are determined WITHOUT seeing the evaluation scores. This ensures business context drives weighting, not analysis quality.

2. **Store-Type Consistency**: Similar stores should have similar weight distributions. A coffee shop in Shanghai should have similar weights to a coffee shop in New York (adjusted for local context).

3. **Justification is Key**: The LLM must explain WHY these weights make sense for THIS specific store type and business model.

4. **Flexibility Within Ranges**: The ranges provide guidance, but specific business details may justify weights outside typical ranges.

---

## Examples

### Example 1: Boutique Coffee Shop (Cozy, Targeting Professionals)
```
Customer: 0.32 - Important to match demographics of professionals
Traffic: 0.38 - Critical for morning commuter traffic
Competition: 0.30 - Differentiation through ambiance and quality
```

### Example 2: Convenience Store (24/7, General Public)
```
Customer: 0.25 - Serves broad population, less targeting needed
Traffic: 0.45 - Location and accessibility are paramount
Competition: 0.30 - Location matters more than differentiation
```

### Example 3: Fine Dining Restaurant (Upscale, Destination)
```
Customer: 0.40 - Must target high-income demographic precisely
Traffic: 0.30 - Destination dining, less dependent on foot traffic
Competition: 0.30 - Differentiation through cuisine and experience
```
