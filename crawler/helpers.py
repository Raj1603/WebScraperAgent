import json, re
from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# Existing utilities
# -------------------------------
def parse_json_safe(text):
    if not text or not isinstance(text, str):
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first != -1 and last != -1:
        try:
            return json.loads(cleaned[first:last+1])
        except Exception:
            pass
    first, last = cleaned.find("["), cleaned.rfind("]")
    if first != -1 and last != -1:
        try:
            return json.loads(cleaned[first:last+1])
        except Exception:
            pass
    return None


def ensure_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def merge_unique_preserve_order(existing, new, key_fn=lambda x: x):
    seen = {key_fn(x) for x in existing if key_fn(x) is not None}
    out = list(existing)
    for item in new:
        k = key_fn(item)
        if k not in seen:
            out.append(item)
            seen.add(k)
    return out


def merge_decision_makers(existing, new):
    existing = existing or []
    new = new or []
    lookup = {(d.get("Name") or "").strip().lower(): d for d in existing if d.get("Name")}
    for d in new:
        name = (d.get("Name") or "").strip()
        key = name.lower()
        if not name:
            lookup[f"_anon_{len(lookup)+1}"] = d
        elif key in lookup:
            base = lookup[key]
            for f, v in d.items():
                if not base.get(f) and v:
                    base[f] = v
            lookup[key] = base
        else:
            lookup[key] = d
    return list(lookup.values())


async def ask_gpt(prompt, model="gpt-4o-mini"):
    res = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,  # generous output allowance
    )
    return res.choices[0].message.content.strip()


# -------------------------------
# New robust crawler helpers
# -------------------------------
def chunk_text(s: str, max_chars: int = 12000):
    """
    Split long page text into smaller chunks for GPT without losing data.
    """
    if not s:
        return []
    if len(s) <= max_chars:
        return [s]

    # split roughly by double newlines or headings
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


def merge_field_value(existing_val, new_val):
    """
    Merge strings or lists intelligently.
    - Strings: keep first non-N/A.
    - Lists: union preserving order.
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


def sanitize_links(links, base_domain):
    """
    Guarantee a proper list of internal URLs; filter out JS/mailto/etc.
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
