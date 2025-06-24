import os, re, requests
from typing import Dict, Optional
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import gender_guesser.detector as gd

load_dotenv()                                # picks up PROXYCURL_API_KEY
PC_KEY = os.getenv("PROXYCURL_API_KEY")

UA = {"User-Agent": "Mozilla/5.0 (EmailResolver/4.0)"}
TITLE_RE = re.compile(r"^(mr|ms|mrs|miss|dr|prof|sir|madam|mx)\.?$", re.I)

# -----------------------------------------------------------------------
# 0. generic helpers
# -----------------------------------------------------------------------
def _http(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    r = requests.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text

def _best(val_old: Optional[str], val_new: Optional[str]) -> Optional[str]:
    """Choose the 'better' string (longer & non‑empty wins)."""
    if not val_new:
        return val_old
    if not val_old:
        return val_new
    return val_new if len(val_new) > len(val_old) else val_old

def _gender(first: Optional[str], title: Optional[str]) -> Optional[str]:
    if title and title.lower() in {"mr", "sir"}:
        return "male"
    if title and title.lower() in {"ms", "mrs", "miss", "madam"}:
        return "female"
    if first:
        try:
            g = gd.Detector(case_sensitive=False)
            guess = g.get_gender(first.split("-")[0])
            if guess in {"male", "mostly_male"}:
                return "male"
            if guess in {"female", "mostly_female"}:
                return "female"
        except ImportError:
            pass
    return None

def _clean_position(txt: str) -> str:
    return re.sub(r"\s+", " ", re.split(r"[,()\n]", txt, 1)[0]).strip()

# -----------------------------------------------------------------------
# 1. your *existing* page‑only resolver, untouched (short version)
# -----------------------------------------------------------------------
def _resolve_from_page(email: str, url: str) -> Dict[str, Optional[str]]:
    rv = dict.fromkeys(("first_name", "last_name", "title", "position", "gender"))
    try:
        soup = BeautifulSoup(_http(url), "html.parser")
    except Exception:
        return rv

    lpart = email.split("@", 1)[0].lower()
    heading = None
    for tag in soup.find_all(["h1", "h2", "h3"]):
        if lpart in tag.get_text(" ", strip=True).lower():
            heading = tag.get_text(" ", strip=True)
            break
    if not heading and soup.h1:
        heading = soup.h1.get_text(" ", strip=True)

    if heading:
        m = re.match(r"(?:(Mr|Ms|Mrs|Miss|Dr|Prof|Sir|Madam|Mx)\.?\s+)?(.+)", heading, re.I)
        if m:
            raw_title, rest = m.groups()
            if raw_title:
                rv["title"] = raw_title.title()
            tokens = rest.split()
            rv["first_name"] = tokens[0] if tokens else None
            rv["last_name"]  = tokens[-1] if len(tokens) > 1 else None
            after = rest[len(" ".join(tokens[:2 if len(tokens)>1 else 1])):].strip()
            if after:
                rv["position"] = _clean_position(after)

    rv["gender"] = _gender(rv["first_name"], rv["title"])
    if rv["gender"] and not rv["title"]:
        rv["title"] = "Mr" if rv["gender"] == "male" else "Ms"
    return rv

# -----------------------------------------------------------------------
# 2. LinkedIn enrichment via Proxycurl
# -----------------------------------------------------------------------
def _proxycurl(link: str) -> Dict[str, Optional[str]]:
    if not PC_KEY:
        return {}
    try:
        r = requests.get(
            "https://nubela.co/proxycurl/api/v2/linkedin",
            headers={"Authorization": f"Bearer {PC_KEY}"},
            params={
                "url": link,
                "extra": "include",      # ask for gender/other extras :contentReference[oaicite:0]{index=0}
                "use_cache": "if-recent"
            },
            timeout=30,
        )
        if r.status_code == 404:
            return {}                   # profile not public / removed
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    return {
        "first_name": data.get("first_name"),
        "last_name":  data.get("last_name"),
        "position":   _clean_position(data.get("headline") or ""),
        "gender":     data.get("gender") or None
    }

# -----------------------------------------------------------------------
# 3. master resolver
# -----------------------------------------------------------------------
def resolve_person(email: str, page_url: str) -> Dict[str, Optional[str]]:
    res = _resolve_from_page(email, page_url)
    # res = dict.fromkeys(("first_name", "last_name", "title", "position", "gender"))

    # If every field already present, skip LinkedIn
    if all(res.values()):
        return res

    # find first LinkedIn link
    try:
        soup = BeautifulSoup(_http(page_url), "html.parser")
        a = soup.find("a", href=lambda h: h and "linkedin.com/in/" in h.lower())
    except Exception:
        a = None

    if a:
        li = _proxycurl(a["href"])
        # merge, preferring the more complete/longer value
        for k in ("first_name", "last_name", "position"):
            res[k] = _best(res.get(k), li.get(k))
        # gender from LinkedIn beats guess
        if li.get("gender"):
            res["gender"] = li["gender"]
        # final gender-based title fill
        if res["gender"] and not res["title"]:
            res["title"] = "Mr" if res["gender"] == "male" else "Ms"

    return res

def get_lengths(res: Dict) -> int:
    return sum(len(v or "") for v in res)
def resolve_person_links(email: str, urls: list) -> Dict:
    best = {}
    for url in urls:
        res = resolve_person(email, url)
        if not best or (get_lengths(res) > get_lengths(best)):
            best = res
    print(f"For {email} resolved: {best}")
    return best

# print(resolve_person(
#     "anwari@rosepartner.de",
#     "https://www.rosepartner.de/en/team/maria-anwari-llm.html"))

# print(resolve_person_links(
#     "anwari@rosepartner.de",
#     ["https://www.rosepartner.de/en/team/maria-anwari-llm.html", "https://www.linkedin.com/in/maria-a-537792136/"]))

# print(resolve_person(
#     "andresen@rosepartner.de",
#     "https://www.rosepartner.de/en/team/dr-jan-eike-andresen.html"))


# print(resolve_person(
#     "support@wooga.net",
#     "https://www.wooga.com/legal"))
