import json, re
from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# JSON Parsing & Cleanup
# -------------------------------
def parse_json_safe(text):
    """
    Parse JSON even if wrapped in markdown fences or extra text.
    """
    if not text or not isinstance(text, str):
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first != -1 and last != -1:
        try:
            return json.loads(cleaned[first:last + 1])
        except Exception:
            pass
    first, last = cleaned.find("["), cleaned.rfind("]")
    if first != -1 and last != -1:
        try:
            return json.loads(cleaned[first:last + 1])
        except Exception:
            pass
    return None


# -------------------------------
# Generic Utilities
# -------------------------------
def ensure_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def merge_unique_preserve_order(existing, new, key_fn=lambda x: x):
    """
    Merge lists preserving order and uniqueness by a given key function.
    """
    seen = {key_fn(x) for x in existing if key_fn(x) is not None}
    out = list(existing)
    for item in new:
        k = key_fn(item)
        if k not in seen:
            out.append(item)
            seen.add(k)
    return out


def merge_decision_makers(existing, new):
    """
    Merge Decision Maker dictionaries by Name (case-insensitive).
    """
    existing = existing or []
    new = new or []
    lookup = {(d.get("Name") or "").strip().lower(): d for d in existing if d.get("Name")}
    for d in new:
        if not isinstance(d, dict):
            continue
        name = (d.get("Name") or "").strip().lower()
        if not name:
            lookup[f"_anon_{len(lookup)+1}"] = d
        elif name in lookup:
            base = lookup[name]
            for f, v in d.items():
                if not base.get(f) and v and v != "N/A":
                    base[f] = v
        else:
            lookup[name] = d
    return list(lookup.values())


async def ask_gpt(prompt, model="gpt-4o-mini"):
    """
    Run async LLM call with safe defaults.
    """
    res = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
    )
    return res.choices[0].message.content.strip()


# -------------------------------
# Deep Merge Utilities
# -------------------------------
def merge_field_value(existing_val, new_val):
    """
    Merge individual scalar or list field values:
    - Keep first non-N/A value for strings.
    - Union + deduplicate for lists.
    """
    def ensure_list_inner(v):
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    if isinstance(existing_val, list) or isinstance(new_val, list):
        a = ensure_list_inner(existing_val)
        b = ensure_list_inner(new_val)
        seen, out = set(), []
        for x in a + b:
            if x and x != "N/A" and x not in seen:
                out.append(x)
                seen.add(x)
        return out
    return existing_val if existing_val and existing_val != "N/A" else (new_val or "N/A")


def merge_nested_dicts(base, update):
    """
    Merge nested dictionaries like Main Office data.
    Prefers first valid, non-N/A values but fills missing keys.
    """
    if not isinstance(base, dict):
        return update or {}
    if not isinstance(update, dict):
        return base
    result = dict(base)
    for k, v in update.items():
        if not result.get(k) or result[k] in ["", "N/A", None]:
            result[k] = v
    return result


def merge_branches(existing, new):
    """
    Merge branches (list of dicts) by Address field.
    Preserves associated Phone/Email fields.
    """
    if not existing:
        return new or []
    if not new:
        return existing

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


# -------------------------------
# Text Splitting for Large Pages
# -------------------------------
def chunk_text(s: str, max_chars: int = 16000):
    """
    Split large pages into smaller chunks to stay under GPT context limit.
    """
    if not s:
        return []
    if len(s) <= max_chars:
        return [s]

    parts = re.split(r"(?m)^(#{1,6}\s.*$)|\n\s*\n", s)
    parts = [p for p in parts if p and p.strip()]
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 2 > max_chars:
            if cur.strip():
                chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur.strip():
        chunks.append(cur)
    return chunks


# -------------------------------
# Link Cleaning
# -------------------------------
def sanitize_links(links, base_domain):
    """
    Ensure valid internal links only.
    """
    if not links:
        return []
    safe = list(links) if not isinstance(links, list) else links
    out = []
    for u in safe:
        try:
            if isinstance(u, str) and base_domain in u and u.startswith("http"):
                out.append(u)
        except Exception:
            continue
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq
