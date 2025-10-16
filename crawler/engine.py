import json, asyncio
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler
from .helpers import (
    parse_json_safe, ensure_list, merge_unique_preserve_order,
    merge_decision_makers, ask_gpt
)
from .prompts import extraction_prompt, link_recommendation_prompt

async def crawl_ai_collect(url: str, geo_location="N/A", max_pages=20):
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

        while to_visit and len(visited) < max_pages:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            print(f"[Crawl] {current}")
            try:
                res = await crawler.arun(url=current)
            except Exception as e:
                print(f"  ! failed: {e}")
                continue

            markdown = res.markdown or ""
            prompt = extraction_prompt(markdown, geo_location)
            raw = await ask_gpt(prompt)
            data = parse_json_safe(raw) or {}

            main_addr = data.get("Main Office Address")
            if main_addr and main_addr != "N/A" and collected["Main Office Address"] == "N/A":
                collected["Main Office Address"] = main_addr

            collected["Other Branches"] = merge_unique_preserve_order(
                collected["Other Branches"], ensure_list(data.get("Other Branches"))
            )
            collected["Main Phone Number"] = merge_unique_preserve_order(
                ensure_list(collected["Main Phone Number"]), ensure_list(data.get("Main Phone Number"))
            )
            collected["Email Address"] = merge_unique_preserve_order(
                ensure_list(collected["Email Address"]), ensure_list(data.get("Email Address"))
            )
            li = data.get("Official Company LinkedIn URL")
            if li and li != "N/A" and collected["Official Company LinkedIn URL"] == "N/A":
                collected["Official Company LinkedIn URL"] = li

            collected["Decision Makers"] = merge_decision_makers(
                collected["Decision Makers"], ensure_list(data.get("Decision Makers"))
            )

            # stop if we have enough info
            if collected["Main Office Address"] != "N/A" and collected["Decision Makers"]:
                break

            missing = []
            if collected["Main Office Address"] == "N/A" and not collected["Other Branches"]:
                missing.append("address")
            if not collected["Main Phone Number"]:
                missing.append("phone")
            if not collected["Email Address"]:
                missing.append("email")
            if not collected["Decision Makers"]:
                missing.append("decision makers")

            if missing:
                link_prompt = link_recommendation_prompt(markdown, base_domain, missing)
                suggested = await ask_gpt(link_prompt)
                urls = parse_json_safe(suggested) or []
                for u in urls:
                    if base_domain in u and u not in visited and len(to_visit) < max_pages:
                        to_visit.append(u)

        return collected
