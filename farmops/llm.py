"""Neural in / neural out. Uses Gemini when GEMINI_API_KEY is set, otherwise a keyword fallback
so the demo always runs offline."""
import json
import os
import re

from . import scenario as S

PARSE_SCHEMA_HINT = """Return JSON only, with keys:
  "fault_codes": list of fault codes mentioned (e.g. "HYD-217"),
  "down_machines": list of machine names that are broken,
  "rain_day": day the rain arrives (Mon/Tue/Wed/Thu/Fri) or null,
  "elevator_backed_up": true/false,
  "priorities": list of field names the supervisor wants first,
  "budget_limit": integer dollars or null"""

MODEL = "gemini-2.5-flash"


def _client():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception:
        return None


def parse_order(text):
    """Supervisor's spoken/typed order -> structured facts."""
    client = _client()
    if client:
        try:
            prompt = (f"You turn a farm supervisor's order into structured facts.\n"
                      f"Known machines: {list(S.COMBINES)}. Known fields: {list(S.FIELDS)}.\n"
                      f"{PARSE_SCHEMA_HINT}\n\nOrder: {text}")
            resp = client.models.generate_content(
                model=MODEL, contents=prompt,
                config={"response_mime_type": "application/json"})
            return json.loads(resp.text), "gemini"
        except Exception as e:
            print(f"  [gemini parse failed, using fallback: {e}]")
    return _fallback_parse(text), "fallback"


def _fallback_parse(text):
    t = text.lower()
    codes = re.findall(r"\b([A-Z]{3}-\d{3})\b", text.upper())
    if not codes and "hydraulic" in t:
        codes = ["HYD-217"]
    down = [m for m in S.COMBINES if m.lower() in t or m.lower().replace("combine ", "combine") in t]
    if not down and re.search(r"combine\s*2", t):
        down = ["Combine 2"]
    rain = next((d for d in ["Mon", "Tue", "Wed", "Thu", "Fri"] if d.lower() in t
                 or {"Thu": "thursday", "Wed": "wednesday", "Tue": "tuesday", "Fri": "friday", "Mon": "monday"}[d] in t), None)
    budget = re.search(r"\$\s?([\d,]+)", text)
    return {
        "fault_codes": codes,
        "down_machines": down,
        "rain_day": rain,
        "elevator_backed_up": "elevator" in t and ("backed" in t or "full" in t or "line" in t),
        "priorities": [f for f in S.FIELDS if f.lower().split()[0] in t],
        "budget_limit": int(budget.group(1).replace(",", "")) if budget else None,
    }


def explain(option, audience):
    """Solver output -> plain language for a specific person."""
    client = _client()
    facts = json.dumps(option, default=str)
    if client:
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=(f"Explain this harvest plan to the {audience} in 2 short sentences. "
                          f"Plain language, no jargon, mention cost and what is at risk. Plan: {facts}"))
            return resp.text.strip()
        except Exception:
            pass
    if audience == "supervisor":
        return (f"{option['name']}: harvests {option['acres_done']} of {option['acres_total']} acres before the rain, "
                f"leaving {option['acres_at_risk']} acres (~${option['grain_at_risk']:,} of grain) exposed. "
                f"Extra spend ${option['extra_cost']:,}.")
    return option["name"]
