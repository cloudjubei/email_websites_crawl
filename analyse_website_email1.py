import os, re, json, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Optional
from dotenv import load_dotenv
import gender_guesser.detector as gd

load_dotenv()                                  # picks up PROXYCURL_API_KEY

# ---------------------------------------------------------------------------
# 0. SMALL HELPERS  (same as before, abridged)
# ---------------------------------------------------------------------------
TITLE_RE = re.compile(r"^(mr|ms|mrs|miss|dr|prof|sir|madam|mx)\.?$", re.I)

def _gender(first: Optional[str], title: Optional[str]) -> Optional[str]:
    if title:
        if title.lower() in {"mr", "sir"}:  return "male"
        if title.lower() in {"ms", "mrs", "miss", "madam"}: return "female"
    if first:
        try:
            g = gd.Detector(case_sensitive=False)
            gfirst = first.split("-")[0]
            res = g.get_gender(gfirst)
            if res in {"male", "mostly_male"}:   return "male"
            if res in {"female", "mostly_female"}: return "female"
        except ImportError:
            pass
    return None

def _clean_position(txt: str) -> str:
    """Minimal clean‑up: strip brackets/commas, squash spaces."""
    return re.sub(r"\s+", " ", re.split(r"[,()]", txt, 1)[0]).strip()

# ---------------------------------------------------------------------------
# 1.  ORIGINAL PAGE‑BASED RESOLVER  (condensed to a helper)
# ---------------------------------------------------------------------------
def resolve_from_page(email: str, url: str) -> Dict[str, Optional[str]]:
    rv = dict.fromkeys(("first_name", "last_name", "title", "position", "gender"))
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    lpart = email.split("@", 1)[0].lower()

    # --- pick heading that mentions the e‑mail local part ---------------
    heading = None
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if lpart in h.get_text(" ", strip=True).lower():
            heading = h.get_text(" ", strip=True)
            break
    if not heading:
        heading = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""

    # --- split “Title First Last <rest>” --------------------------------
    m = re.match(r"(?:(Mr|Ms|Mrs|Miss|Dr|Prof|Sir|Madam|Mx)\.?\s+)?(.+)", heading, re.I)
    if m:
        raw_title, rest = m.groups()
        if raw_title:
            rv["title"] = raw_title.title()
        tokens = rest.split()
        if tokens:
            rv["first_name"] = tokens[0]
            if len(tokens) > 1:
                rv["last_name"] = tokens[-1]
        after_name = rest[len(" ".join(tokens[:2 if len(tokens)>1 else 1])):].strip()
        if after_name:
            rv["position"] = _clean_position(after_name)

    rv["gender"] = _gender(rv["first_name"], rv["title"])
    if not rv["title"] and rv["gender"]:
        rv["title"] = "Mr" if rv["gender"] == "male" else "Ms"
    return rv

# ---------------------------------------------------------------------------
# 2.  LINKEDIN ENRICHMENT VIA PROXYCURL
# ---------------------------------------------------------------------------
PC_API   = "https://nubela.co/proxycurl/api/v2/linkedin"
PC_KEY   = os.getenv("PROXYCURL_API_KEY")

def _enrich_from_linkedin(profile_url: str) -> Dict[str, Optional[str]]:
    print("PC_KEY: ")
    print(PC_KEY)
    if not PC_KEY:
        return {}  # skip if user hasn't set a key
    hdrs = {"Authorization": f"Bearer {PC_KEY}"}
    params = {"url": profile_url, "extra": "include", "use_cache": "if-present"}
    try:
        r = requests.get(PC_API, headers=hdrs, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    out: Dict[str, Optional[str]] = {}
    out["first_name"] = data.get("first_name")
    out["last_name"]  = data.get("last_name")
    # headline is the best single “position” string LinkedIn has
    out["position"]   = _clean_position(data.get("headline") or "")
    # gender, if you fetched `extra=include`
    if "gender" in data:
        out["gender"] = data["gender"]
    return out

# ---------------------------------------------------------------------------
# 3.  MASTER FUNCTION  ------------------------------------------------------
# ---------------------------------------------------------------------------
def resolve_person(email: str, page_url: str) -> Dict[str, Optional[str]]:
    # result = resolve_from_page(email, page_url)
    result = dict.fromkeys(("first_name", "last_name", "title", "position", "gender"))

    # Already complete?  Great, return.
    if all(result.values()):
        return result

    # Find first LinkedIn link on the page
    try:
        html = requests.get(page_url, timeout=10).text
    except Exception:
        html = ""
    soup = BeautifulSoup(html, "html.parser")
    a_tag = soup.find("a", href=lambda h: h and "linkedin.com/" in h.lower())
    if a_tag:
        ld_info = _enrich_from_linkedin(a_tag["href"])
        for k, v in ld_info.items():
            if v and not result.get(k):
                result[k] = v

    # Final gender→title fix‑up
    if not result["title"] and result.get("gender") in {"male", "female"}:
        result["title"] = "Mr" if result["gender"] == "male" else "Ms"

    return result

print(resolve_person(
    "anwari@rosepartner.de",
    "https://www.rosepartner.de/en/team/maria-anwari-llm.html"))

print(resolve_person(
    "andresen@rosepartner.de",
    "https://www.rosepartner.de/en/team/dr-jan-eike-andresen.html"))