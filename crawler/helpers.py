import json, re
from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def parse_json_safe(text):
    if not text or not isinstance(text, str):
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    first, last = cleaned.find("{"), cleaned.rfind("}")
    if first != -1 and last != -1:
        try: return json.loads(cleaned[first:last+1])
        except: pass
    first, last = cleaned.find("["), cleaned.rfind("]")
    if first != -1 and last != -1:
        try: return json.loads(cleaned[first:last+1])
        except: pass
    return None

def ensure_list(val):
    if val is None: return []
    if isinstance(val, list): return val
    return [val]

def merge_unique_preserve_order(existing, new, key_fn=lambda x: x):
    seen = {key_fn(x) for x in existing if key_fn(x) is not None}
    for item in new:
        k = key_fn(item)
        if k not in seen:
            existing.append(item)
            seen.add(k)
    return existing

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
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()
