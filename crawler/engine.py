import re
import json
from urllib.parse import urlparse, urljoin
from crawl4ai import AsyncWebCrawler

from .helpers import (
    parse_json_safe,
    ensure_list,
    merge_decision_makers,
    ask_gpt,
)
from .prompts import extraction_prompt, dynamic_link_prompt


# ---------------------------
# Helpers
# ---------------------------
def extract_internal_links_from_html(html, base_url, base_domain):
    if not html:
        return []
    links = []
    for href in re.findall(r'href=["\'](.*?)["\']', html, re.I):
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            continue
        abs_url = urljoin(base_url, href)
        if base_domain in urlparse(abs_url).netloc:
            links.append(abs_url.rstrip("/"))
    seen, result = set(), []
    for u in links:
        if u not in seen:
            result.append(u)
            seen.add(u)
    return result


def merge_branches(existing, new):
    """
    Merge branch dictionaries (address, phone, email grouped).
    """
    existing_map = {b.get("Address", "").strip().lower(): b for b in existing if isinstance(b, dict)}
    for b in new:
        if not isinstance(b, dict):
            continue
        addr = (b.get("Address") or "").strip().lower()
        if not addr:
            continue
        if addr in existing_map:
            base = existing_map[addr]
            for f in ["Phone", "Email"]:
                if not base.get(f) and b.get(f):
                    base[f] = b[f]
        else:
            existing_map[addr] = b
    return list(existing_map.values())


def is_valid_text(val):
    if not val:
        return False
    if isinstance(val, str) and val.strip().upper() == "N/A":
        return False
    if isinstance(val, str) and re.search(r"(example\.com|john|doe|info@)", val, re.I):
        return False
    return True


def log_diff(label, old, new):
    def fmt(v):
        if isinstance(v, dict):
            return json.dumps(v)[:180]
        if isinstance(v, list):
            return json.dumps(v[:2])[:180]
        return str(v)[:120]

    if old != new:
        print(f"✅ Updated {label}: {fmt(old)} → {fmt(new)}")


# ---------------------------
# MAIN ENGINE
# ---------------------------
async def crawl_ai_collect(url: str, geo_location="N/A", max_pages=20):
    base_domain = urlparse(url).netloc
    visited, to_visit = set(), [url.rstrip("/")]

    collected = {
        "Main Office": {
            "Address": "N/A",
            "Phone": "N/A",
            "Email": "N/A",
            "LinkedIn": "N/A",
        },
        "Branches": [],
        "Decision Makers": [],
    }

    print(f"🌍 Starting structured crawl on: {url}")

    async with AsyncWebCrawler() as crawler:
        while to_visit and len(visited) < max_pages:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            print(f"\n[Crawl] {current}")

            try:
                res = await crawler.arun(url=current, js_render=True, wait_until="networkidle")
            except Exception as e:
                print(f"  ! failed: {e}")
                continue

            html = res.html or ""
            markdown = res.markdown or html
            internal_links = extract_internal_links_from_html(html, current, base_domain)
            print(f"📄 Extracted {len(markdown)} chars | {len(internal_links)} links")

            raw = await ask_gpt(extraction_prompt(markdown, geo_location))
            data = parse_json_safe(raw) or {}

            # ---- Merge Main Office ----
            new_main = data.get("Main Office", {})
            for key in ["Address", "Phone", "Email", "LinkedIn"]:
                val = new_main.get(key)
                if is_valid_text(val) and collected["Main Office"].get(key, "N/A") in ["N/A", None, ""]:
                    log_diff(f"Main Office {key}", collected["Main Office"].get(key), val)
                    collected["Main Office"][key] = val

            # ---- Merge Branches ----
            new_branches = data.get("Branches", [])
            if isinstance(new_branches, list) and new_branches:
                merged = merge_branches(collected["Branches"], new_branches)
                if merged != collected["Branches"]:
                    log_diff("Branches", collected["Branches"], merged)
                    collected["Branches"] = merged

            # ---- Merge Decision Makers ----
            new_dms = data.get("Decision Makers", [])
            merged_dms = merge_decision_makers(collected["Decision Makers"], new_dms)
            if merged_dms != collected["Decision Makers"]:
                log_diff("Decision Makers", collected["Decision Makers"], merged_dms)
                collected["Decision Makers"] = merged_dms

            # ---- Determine missing fields ----
            missing = []
            if not is_valid_text(collected["Main Office"].get("Address")):
                missing.append("address")
            if not is_valid_text(collected["Main Office"].get("Phone")):
                missing.append("phone")
            if not is_valid_text(collected["Main Office"].get("Email")):
                missing.append("email")
            if not collected["Decision Makers"]:
                missing.append("decision makers")

            if not missing:
                print("✅ Data sufficiently complete. Stopping crawl.")
                break

            print(f"🧩 Missing fields: {missing}")

            # ---- Next links ----
            suggested_urls = []
            if internal_links:
                prompt = dynamic_link_prompt(markdown, internal_links, missing, base_domain)
                suggested = await ask_gpt(prompt)
                urls = parse_json_safe(suggested) or []
                if isinstance(urls, list):
                    suggested_urls = [
                        u.rstrip("/")
                        for u in urls
                        if base_domain in (urlparse(u).netloc or "")
                    ]
            for u in suggested_urls:
                if u not in visited and len(to_visit) < max_pages:
                    to_visit.append(u)
            print(f"🤖 AI suggests {len(suggested_urls)} URLs to explore.")

        print(f"\n✅ Crawl completed. {len(visited)} pages visited.")
        return collected
