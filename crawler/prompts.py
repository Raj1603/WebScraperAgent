# import json

# def extraction_prompt(markdown, geo_location="N/A"):
#     """
#     Strict extraction prompt for a single full page or chunk.
#     The geo_location hint helps GPT prefer relevant addresses/phones.
#     """
#     return f"""
# Geo Location: {geo_location}
# You are a strict information extraction agent.

# Rules:
# - ONLY extract text that is explicitly visible in the content below.
# - DO NOT make up or infer any names, emails, or phone numbers.
# - If you do not see the data, return exactly "N/A" (for strings) or [] (for arrays).
# - Never use placeholder values (like John Smith, info@company.com, etc.).
# - Prefer addresses, phone numbers, and people relevant to {geo_location}.
# - Be factual and concise.

# Extract exactly this JSON:
# {{
#   "Main Office Address": "N/A or string",
#   "Other Branches": [],
#   "Main Phone Number": [],
#   "Email Address": [],
#   "Official Company LinkedIn URL": "N/A or string",
#   "Decision Makers": [
#     {{
#       "Name": "N/A or string",
#       "Title": "N/A or string",
#       "Email": "N/A or string",
#       "Phone": "N/A or string",
#       "LinkedIn": "N/A or string",
#       "ProfileURL": "N/A or string"
#     }}
#   ]
# }}

# --- FULL WEBPAGE CONTENT BELOW ---
# {markdown}
# --- END ---
# """


# def dynamic_link_prompt(markdown, links, missing_fields, base_domain):
#     """
#     Lets the LLM intelligently choose which internal links (discovered by Crawl4AI)
#     are most likely to contain the missing information.
#     """
#     # Convert links to a safe JSON list
#     safe_links = list(links) if links else []

#     return f"""
# You are an intelligent web exploration agent.

# Goal:
# Find the missing fields: {', '.join(missing_fields)}.

# You are given:
# 1. The visible text of the current webpage.
# 2. The internal links already discovered on this page (below).

# Rules:
# - Choose ONLY links that are most likely to contain the missing data.
# - Links must belong to the same domain: {base_domain}.
# - DO NOT make up or guess any URLs.
# - Return ONLY a JSON array of URLs from the provided list, nothing else.

# --- PAGE CONTENT ---
# {markdown}
# --- INTERNAL LINKS FOUND (JSON) ---
# {json.dumps(safe_links, indent=2)}
# --- END ---
# """

import json

def extraction_prompt(markdown, geo_location="N/A"):
    """
    Strict structured extraction prompt for company contact data.
    Keeps phone, email, and address grouped per branch.
    """
    return f"""
Geo Location: {geo_location}
You are a structured data extraction agent.

Rules:
- DO NOT invent or assume anything — only extract data visible in the content.
- If something is missing, set its value to "N/A" or [].
- Do NOT use placeholder names like John Doe, info@example.com, etc.
- Group branch data together (address, phone, email in same object).
- Keep all addresses and contact info relevant to {geo_location}.
- Prefer complete, well-formed addresses over partial ones.

Return valid JSON exactly in this schema:
{{
  "Main Office": {{
    "Address": "N/A or string",
    "Phone": "N/A or string",
    "Email": "N/A or string",
    "LinkedIn": "N/A or string"
  }},
  "Branches": [
    {{
      "Address": "N/A or string",
      "Phone": "N/A or string",
      "Email": "N/A or string"
    }}
  ],
  "Decision Makers": [
    {{
      "Name": "N/A or string",
      "Title": "N/A or string",
      "Email": "N/A or string",
      "Phone": "N/A or string",
      "LinkedIn": "N/A or string",
      "ProfileURL": "N/A or string"
    }}
  ]
}}

--- WEBPAGE CONTENT BELOW ---
{markdown}
--- END ---
"""


def dynamic_link_prompt(markdown, links, missing_fields, base_domain):
    """
    Lets the LLM choose which internal links are most likely to contain missing info.
    """
    safe_links = list(links) if links else []

    return f"""
You are a web exploration planner.

We are still missing: {', '.join(missing_fields)}.

Here is the page content and internal links discovered.
Choose up to 6 internal URLs from the list below that are most likely to contain
the missing information (e.g. About, Contact, Locations, Team, Leadership).

Rules:
- Pick only URLs that belong to {base_domain}.
- Do not fabricate or assume URLs.
- Return ONLY a JSON list of URLs.

--- PAGE TEXT (trimmed) ---
{markdown}
--- LINKS ---
{json.dumps(safe_links, indent=2)}
--- END ---
"""
