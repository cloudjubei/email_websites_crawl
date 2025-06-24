import os, random, re, requests, html
from typing import List, Dict, Optional
from urllib.parse import urlencode
from pprint import pprint

SEARXNG_URLS = [
    # "https://search.citw.lgbt",
    "https://searx.foobar.vip/",
    # "https://opnxng.com/",
    # "https://search.indst.eu/",
    # "https://searx.stream/",
    # "https://search.hbubli.cc/",
    # "https://priv.au/",
    # "https://searx.be",                # EU
    # "https://searx.tiekoetter.com",    # EU
    # "https://searxng.darmarit.org",    # EU
    # "https://search.mdosch.de",        # EU
    # "https://searx.xyz",               # US
    # "https://searx.rhscz.eu/",
    # "https://searx.tuxcloud.net/"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (SearXNG-Resolver/1.0)"}

def _searxng_request(query: str, base: str, num: int = 20) -> List[Dict]:
    """
    Query a SearXNG instance and return a list of result dicts:
        {title, url, content}
    """

    url = f"{base.rstrip('/')}/search"
    params = {
        "q": query,
        # "format": "json",
        "engines": "google,bing,duckduckgo,brave",
        "language": "en",
        # "safesearch": 0,
        "safesearch": 1,
        # "timeout": 2000,
    }
    # //search?q=anwari%40rosepartner.de&category_general=1&language=en&time_range=&safesearch=1&theme=simple

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        print("REQUEST ERROR:")
        print(e)
        return []

    print("REQUEST RESPONSE:")
    print(j)

    return [
        {
            "title": html.unescape(item.get("title", "")),
            "link": item.get("url", ""),
            "snippet": html.unescape(item.get("content", "")),
        }
        for item in j.get("results", [])[:num]
    ]

# — 1)  NAME  ➜  LinkedIn profile URL
def find_linkedin_by_name(first: str, last: str, top_k=20) -> Optional[str]:
    q = f'"{first} {last}" site:linkedin.com/in/'

    for url in SEARXNG_URLS:
        for r in _searxng_request(q, url, top_k):
            if "linkedin.com/in/" in r["link"]:
                return r["link"]
    return None


# — 2)  EMAIL ➜  LinkedIn profile URL
def find_linkedin_by_email(email: str, top_k=20) -> Optional[str]:
    # q = f'"{email}" site:linkedin.com/in/'
    q = f'"{email}"'

    for url in SEARXNG_URLS:
        for r in _searxng_request(q, url, top_k):
            if "linkedin.com/in/" in r["link"]:
                return r["link"]
    return None


# — 3)  EMAIL ➜  First non‑LinkedIn profile / bio page
_profile_hint = re.compile(r"\b(profile|team|staff|about|bio|cv|vitae|faculty)\b", re.I)

def find_profile_by_email_nonlinkedin(email: str, top_k=20) -> Optional[Dict]:
    q = f'"{email}" -site:linkedin.com'

    for url in SEARXNG_URLS:
        for r in _searxng_request(q, url, top_k):
            if "linkedin.com" in r["link"]:
                continue
            blob = (r["title"] + " " + r["snippet"]).lower()
            if _profile_hint.search(blob):
                return r
    return None

if __name__ == "__main__":
    # print("\n— Name → LinkedIn —")
    # print(find_linkedin_by_name("Jan‑Eike", "Andresen"))

    print("\n— Email → LinkedIn —")
    print(find_linkedin_by_email("anwari@rosepartner.de"))

    # print("\n— Email → other profile page —")
    # pprint(find_profile_by_email_nonlinkedin("andresen@rosepartner.de"))