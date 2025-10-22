import json, asyncio, re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler
from .helpers import (
    parse_json_safe, ensure_list, merge_unique_preserve_order,
    merge_decision_makers, ask_gpt,
    chunk_text, merge_field_value, sanitize_links
)
from .prompts import extraction_prompt, dynamic_link_prompt


# --------------------- Field Validation ---------------------
def is_valid_field(value, field_name=""):
    """Reject placeholders, empty, or meaningless values."""
    if not value or value == "N/A":
        return False
    if isinstance(value, str):
        low = value.lower()
        if any(p in low for p in ["john", "doe", "example", "headquarter", "office", "info@", "email us"]):
            return False
        if field_name == "email" and not re.search(r"[\w\.-]+@[\w\.-]+\.\w+", value):
            return False
        if field_name == "phone" and not re.search(r"\d{2,}", value):
            return False
    return True


async def crawl_ai_collect(url: str, geo_location="N/A", max_pages=25):
    """
    Dynamic Crawl4AI-based web agent:
    - Crawls recursively through internal links discovered by Crawl4AI.
    - Extracts company information using GPT.
    - Keeps crawling until all required fields are valid or pages exhausted.
    """

    async with AsyncWebCrawler() as crawler:
        base_domain = urlparse(url).netloc
        visited, to_visit = set(), [url]

        collected = {
            "Main Office Address": "N/A",
            "Other Branches": [],
            "Main Phone Number": [],
            "Email Address": [],
            "Official Company LinkedIn URL": "N/A",
            "Decision Makers": []
        }

        print(f"🌍 Starting deep intelligent crawl on: {url}")

        while to_visit and len(visited) < max_pages:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)

            print(f"\n[Crawl] {current}")
            try:
                res = await crawler.arun(url=current, js_render=True, wait_until="networkidle")
            except Exception as e:
                print(f"  ! Failed to fetch {current}: {e}")
                continue

            markdown = res.markdown or res.html or ""
            internal_links = sanitize_links(getattr(res, "links", []), base_domain)
            print(f"📄 Extracted {len(markdown)} chars | {len(internal_links)} internal links")

            # If page content too thin, fallback to raw HTML
            if len(markdown.strip()) < 200:
                markdown = res.html or ""

            # -------- Step 1: Extract structured info (chunk-wise) --------
            chunks = chunk_text(markdown, max_chars=12000)
            page_data = {k: "N/A" if isinstance(v, str) else [] for k, v in collected.items()}

            for chunk in chunks:
                prompt = extraction_prompt(chunk, geo_location)
                raw = await ask_gpt(prompt)
                data = parse_json_safe(raw) or {}

                page_data["Main Office Address"] = merge_field_value(
                    page_data["Main Office Address"], data.get("Main Office Address")
                )
                page_data["Other Branches"] = merge_unique_preserve_order(
                    page_data["Other Branches"], ensure_list(data.get("Other Branches"))
                )
                page_data["Main Phone Number"] = merge_unique_preserve_order(
                    ensure_list(page_data["Main Phone Number"]),
                    ensure_list(data.get("Main Phone Number"))
                )
                page_data["Email Address"] = merge_unique_preserve_order(
                    ensure_list(page_data["Email Address"]),
                    ensure_list(data.get("Email Address"))
                )
                li = data.get("Official Company LinkedIn URL")
                if li and li != "N/A" and page_data["Official Company LinkedIn URL"] == "N/A":
                    page_data["Official Company LinkedIn URL"] = li
                page_data["Decision Makers"] = merge_decision_makers(
                    page_data["Decision Makers"], ensure_list(data.get("Decision Makers"))
                )

            # -------- Step 2: Merge results globally --------
            for k in collected:
                if k in ("Main Office Address", "Official Company LinkedIn URL"):
                    collected[k] = merge_field_value(collected[k], page_data.get(k))
                elif k in ("Other Branches", "Main Phone Number", "Email Address"):
                    collected[k] = merge_unique_preserve_order(
                        ensure_list(collected[k]), ensure_list(page_data.get(k))
                    )
                elif k == "Decision Makers":
                    collected[k] = merge_decision_makers(collected[k], page_data.get(k))

            # -------- Step 3: Determine still-missing fields --------
            missing = []
            if not is_valid_field(collected["Main Office Address"], "address"):
                missing.append("address")
            if not any(is_valid_field(p, "phone") for p in ensure_list(collected["Main Phone Number"])):
                missing.append("phone")
            if not any(is_valid_field(e, "email") for e in ensure_list(collected["Email Address"])):
                missing.append("email")
            if not any(is_valid_field(dm.get("Name")) for dm in collected["Decision Makers"]):
                missing.append("decision makers")

            # Continue exploring until nothing left to try
            if not missing:
                print("✅ All required fields found — stopping crawl.")
                break

            print(f"⚠️ Still missing: {missing}")

            # -------- Step 4: Ask GPT which internal links might help --------
            link_prompt = dynamic_link_prompt(markdown, internal_links, missing, base_domain)
            suggested = await ask_gpt(link_prompt)
            urls = parse_json_safe(suggested) or []

            urls = [
                u for u in urls
                if isinstance(u, str)
                and base_domain in u
                and not u.startswith("javascript:")
                and u not in visited
                and len(to_visit) < max_pages
            ]

            print(f"🤖 AI suggested {len(urls)} new links to explore.")
            to_visit.extend(urls)

        print(f"\n✅ Crawl finished — {len(visited)} pages visited.")
        return collected
