def extraction_prompt(markdown, geo_location="N/A"):
    return f"""
Geo Location: {geo_location}
Extract and return ONLY valid JSON with these exact keys:
- "Main Office Address"
- "Other Branches"
- "Main Phone Number"
- "Email Address"
- "Official Company LinkedIn URL"
- "Decision Makers" (array of objects: Name, Title, Email, Phone, LinkedIn, ProfileURL)

Return JSON only. No text outside JSON.
--- Webpage content (truncated) ---
{markdown[:8000]}
---
"""

def link_recommendation_prompt(markdown, base_domain, missing_fields):
    return f"""
Given this company's webpage content (below), some fields are missing: {', '.join(missing_fields)}.
Suggest up to 6 internal URLs (full links) likely to contain missing data (like Contact, About, Locations, Team, etc.)
Return JSON array of URLs only.
---
{markdown[:8000]}
---
"""
