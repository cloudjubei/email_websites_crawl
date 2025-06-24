from __future__ import annotations
import re, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Optional
import gender_guesser.detector as gd

UA = {"User-Agent": "Mozilla/5.0 (EmailResolver/3.0)"}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
TITLE_RE = re.compile(r"^(mr|ms|mrs|miss|dr|prof|sir|madam|mx)\.?$", re.I)

def _fetch(url: str) -> Optional[str]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = requests.get(url, headers=UA, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except:
        return None

def _gender(first: Optional[str], title: Optional[str]) -> Optional[str]:
    if title:
        t = title.lower()
        if t in {"mr", "sir"}: return "male"
        if t in {"ms", "mrs", "miss", "madam"}: return "female"
    if first:
        try:
            base = first.split("-")[0]
            g = gd.Detector(case_sensitive=False).get_gender(base)
            if g in {"male", "mostly_male"}: return "male"
            if g in {"female", "mostly_female"}: return "female"
        except ImportError:
            pass
    return None

def _vcard(block: BeautifulSoup, base: str) -> Dict[str, str]:
    link = block.find("a", href=lambda h: h and h.lower().endswith(".vcf"))
    if not link: return {}
    card = _fetch(urljoin(base, link["href"]))
    out = {}
    if card:
        for line in card.splitlines():
            if ":" not in line: continue
            tag, val = line.split(":", 1)
            tag = tag.split(";")[0].upper()
            val = val.strip()
            if tag == "FN":
                out.update(_split_heading(val))
            elif tag == "N":
                parts = val.split(";")
                if len(parts) >= 2:
                    out["last_name"], out["first_name"] = parts[:2]
            elif tag in {"TITLE", "ROLE"}:
                out["position"] = val
    return out

def _split_heading(text: str) -> Dict[str, Optional[str]]:
    out = dict.fromkeys(("title", "first_name", "last_name", "position"))
    text = " ".join(text.strip().split())

    # Break text into name section and role/position
    match = re.match(r"(?:(Mr|Ms|Mrs|Miss|Dr|Prof|Sir|Madam|Mx)\.?\s+)?([\w\-]+(?:\s+[\w\-]+)*)(.*)", text, re.I)
    if not match:
        return out

    raw_title, name_part, position_part = match.groups()

    tokens = name_part.split()
    if tokens:
        out["first_name"] = tokens[0]
        if len(tokens) > 1:
            out["last_name"] = tokens[-1]

    if raw_title:
        out["title"] = raw_title.title()

    if position_part:
        out["position"] = position_part.strip(" ,–—\t")

    return out

def resolve_person(email: str, page_url: str) -> Dict[str, Optional[str]]:
    rv = dict.fromkeys(("first_name", "last_name", "title", "position", "gender"))
    html = _fetch(page_url)
    if not html:
        return rv

    soup = BeautifulSoup(html, "html.parser")
    lpart = email.split("@", 1)[0].lower()

    # Find element likely containing the name / email
    best_block = None
    for tag in soup.find_all(["h1", "h2", "h3", "p", "div"]):
        if lpart in tag.get_text(" ", strip=True).lower():
            best_block = tag
            break

    if not best_block:
        best_block = soup.find(["h1", "h2", "h3", "p", "div"])

    if best_block:
        text = best_block.get_text(" ", strip=True)
        rv.update({k: v for k, v in _split_heading(text).items() if v})

    # Look for vCard — overrides everything else
    rv.update({k: v for k, v in _vcard(best_block or soup, page_url).items() if v})

    # Set gender → title fallback
    rv["gender"] = _gender(rv["first_name"], rv["title"])
    if not rv["title"] and rv["gender"]:
        rv["title"] = "Mr" if rv["gender"] == "male" else "Ms"

    return rv



print(resolve_person(
    "anwari@rosepartner.de",
    "https://www.rosepartner.de/en/team/maria-anwari-llm.html"
))


print(resolve_person(
    "andresen@rosepartner.de",
    "https://www.rosepartner.de/en/team/dr-jan-eike-andresen.html"
))