import os, re, json, time, random, html
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERP_KEY   = os.getenv("SERPAPI_API_KEY")
G_API_KEY  = os.getenv("GOOGLE_API_KEY")
G_CSE_ID   = os.getenv("GOOGLE_CSE_ID")
BRAVE_KEY  = os.getenv("BRAVE_API_KEY")

UA = {"User-Agent": "Mozilla/5.0 (SearchResolver/1.0)"}

# ────────────────────────────────────────────────────────────────────────
def _search_serpapi(q: str, n: int) -> List[Dict]:
    """SerpAPI – best quality (if key present)."""
    if not SERP_KEY:
        return []
    try:
        data = GoogleSearch({"engine": "google", "q": q, "num": n,
                             "api_key": SERP_KEY}).get_dict()
        return data.get("organic_results", [])[:n]
    except Exception:
        return []

def _search_google_cse(q: str, n: int) -> List[Dict]:
    """Google Custom Search JSON API fallback."""
    if not (G_API_KEY and G_CSE_ID):
        return []
    url = "https://www.googleapis.com/customsearch/v1"
    try:
        r = requests.get(url, params={
            "key": G_API_KEY, "cx": G_CSE_ID, "q": q, "num": n
        }, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])[:n]
        return [{"title": i["title"], "link": i["link"],
                 "snippet": html.unescape(i.get("snippet", ""))}
                for i in items]
    except Exception:
        return []

def _search_brave(q: str, n: int) -> List[Dict]:
    """Brave Search API fallback."""
    if not BRAVE_KEY:
        return []
    try:
        r = requests.get("https://api.search.brave.com/res/v1/search",
                         headers={"X-Subscription-Token": BRAVE_KEY,
                                  "Accept": "application/json"},
                         params={"q": q, "source": "news", "count": n},
                         timeout=10)
        r.raise_for_status()
        docs = r.json().get("results", [])[:n]
        return [{"title": d.get("title"), "link": d.get("url"),
                 "snippet": d.get("description", "")} for d in docs]
    except Exception:
        return []

def _scrape_google(q: str, n: int) -> List[Dict]:
    """Last‑ditch HTML scrape (unofficial, obfuscated by Google)."""
    url = "https://www.google.com/search"
    try:
        r = requests.get(url, params={"q": q, "num": n}, headers=UA, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for g in soup.select(".tF2Cxc")[:n]:
            a = g.select_one("a")
            title = g.h3.text if g.h3 else ""
            snip = g.select_one(".VwiC3b") or g.select_one(".aCOpRe")
            out.append({"title": title,
                        "link": a["href"] if a else "",
                        "snippet": snip.text if snip else ""})
        return out
    except Exception:
        return []

def smart_search(query: str, num: int = 5) -> List[Dict]:
    """Try SerpAPI → Google CSE → Brave API → raw scrape (in that order)."""
    for engine in (_search_serpapi, _search_google_cse,
                   _search_brave, _scrape_google):
        res = engine(query, num)
        if res:
            return res
    return []

# 1) name → LinkedIn url
def find_linkedin_by_name(first: str, last: str, top_k=5):
    q = f'"{first} {last}" site:linkedin.com/in'
    for r in smart_search(q, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


# 2) email → LinkedIn url
def find_linkedin_by_email(email: str, top_k=5):
    q = f'"{email}" site:linkedin.com/in'
    for r in smart_search(q, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


# 3) email → FIRST non‑LinkedIn page w/ name or bio
def find_profile_by_email_nonlinkedin(email: str, top_k=10):
    q = f'"{email}" -site:linkedin.com'
    for r in smart_search(q, top_k):
        if "linkedin.com" in r["link"]:
            continue
        # heuristics: look for words that suggest a profile page
        profileish = re.search(r"\b(profile|team|staff|about|bio|cv|vitae|faculty)\b",
                               (r["title"] + r["snippet"]).lower())
        if profileish:
            return r  # dict(title, link, snippet)
    return None

print(find_linkedin_by_name("Jan‑Eike", "Andresen"))

print(find_linkedin_by_email("anwari@rosepartner.de"))

print(find_profile_by_email_nonlinkedin("andresen@rosepartner.de"))
