import time, random, re, html, urllib.parse, requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from pprint import pprint

UA_HDR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}

# ───────────────────────────────────────── search helpers ──────────────

SEARXNG_URLS = [
    # "https://search.citw.lgbt",
    # "https://searx.foobar.vip/",
    # "https://opnxng.com/",
    # "https://search.indst.eu/",
    # "https://searx.stream/",
    # "https://search.hbubli.cc/",
    "https://priv.au/",
    # "https://searx.be",                # EU
    # "https://searx.tiekoetter.com",    # EU
    # "https://searxng.darmarit.org",    # EU
    # "https://search.mdosch.de",        # EU
    # "https://searx.xyz",               # US
    # "https://searx.rhscz.eu/",
    # "https://searx.tuxcloud.net/"
]
def _searchxng(q: str, n: int) -> List[Dict]:
    for base in SEARXNG_URLS:
        url = f"{base.rstrip('/')}/search"
        # //search?q=anwari%40rosepartner.de&category_general=1&language=en&time_range=&safesearch=1&theme=simple

        params = {"q": q, "hl": "en", "language": "en", "safesearch": 1, "time_range": None, "theme": "simple"}
        r = requests.get(url, headers=UA_HDR, params=params, timeout=15)
        r.raise_for_status()

        print("RESULT FROM SEARCHXNG:")
        print(r.text)
        return []
def _searx_html(query: str, n: int) -> List[Dict]:
    base = random.choice(SEARXNG_URLS)
    params = {
        "q": query,
        "format": "html",              # explicit but default
        "language": "en",
        "safesearch": "0",
        "categories": "general",
    }
    try:
        r = requests.get(f"{base}/search", params=params,
                         headers=UA_HDR, timeout=15)
        r.raise_for_status()
        print("RESULT FROM _searx_html:")
        print(r.text)
    except Exception:
        print("ERROR FROM _searx_html:")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select("div.result")[:n]:
        a = res.select_one("h3 > a, a.result__a, a")
        if not a:
            continue
        link = a["href"]
        title = a.get_text(" ", strip=True)
        snippet = res.select_one(".content") or res.select_one(".result-content") \
                  or res.select_one("p")
        out.append({
            "title": title,
            "link": link,
            "snippet": snippet.get_text(" ", strip=True) if snippet else ""
        })
    return out


def _google(q: str, n: int) -> List[Dict]:
    url = "https://www.google.com/search"
    params = {"q": q, "num": n, "hl": "en"}
    r = requests.get(url, headers=UA_HDR, params=params, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    # print("RESULT FROM GOOGLE:")
    # print(r.text)
    for g in soup.select(".tF2Cxc")[:n]:
        link = g.select_one("a")["href"]
        title = g.select_one("h3").text if g.select_one("h3") else ""
        snip = g.select_one(".VwiC3b") or g.select_one(".aCOpRe")
        out.append(
            {"title": title, "link": link, "snippet": snip.text if snip else ""}
        )
    return out


def _duckduckgo(q: str, n: int) -> List[Dict]:
    url = "https://duckduckgo.com/html/"
    params = {"q": q, "s": "0"}
    r = requests.get(url, headers=UA_HDR, params=params, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select(".result")[: n]:
        a = res.select_one("a.result__a")
        if not a:
            continue
        link = html.unescape(a["href"])
        title = a.text
        snip = res.select_one(".result__snippet")
        out.append(
            {"title": title, "link": link, "snippet": snip.text if snip else ""}
        )
    return out


def _bing(q: str, n: int) -> List[Dict]:
    url = "https://www.bing.com/search"
    params = {"q": q, "count": n}
    r = requests.get(url, headers=UA_HDR, params=params, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for li in soup.select("li.b_algo")[: n]:
        a = li.select_one("a")
        if not a:
            continue
        link = a["href"]
        title = a.text
        snip = li.select_one(".b_caption p")
        out.append(
            {"title": title, "link": link, "snippet": snip.text if snip else ""}
        )
    return out


def smart_search_html(query: str, num: int = 10) -> List[Dict]:
    """Try Google → DuckDuckGo → Bing until we get at least one result."""
    all_results = []
    # for engine in (_searchxng, _google, _duckduckgo, _bing):
    for engine in (_searx_html, _google, _duckduckgo, _bing):
        try:
            results = engine(query, num)
            print("RESULTS")
            print(results)
            # if results:
            #     all_results += results
        except Exception:
            pass
        time.sleep(1)  # polite pause between engines
    return all_results

# ──────────────────────────────────────── task helpers ─────────────────
def find_linkedin_by_name(first: str, last: str, top_k: int = 6) -> Optional[str]:
    q = f'"{first} {last}" site:linkedin.com/in'
    for r in smart_search_html(q, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


def find_linkedin_by_email(email: str, top_k: int = 20) -> Optional[str]:
    # q = f'"{email}" site:linkedin.com/in'
    q = f'"{email}"'
    for r in smart_search_html(q, top_k):
        print(r["link"])
        # if "linkedin.com/in/" in r["link"]:
            # return r["link"]
    return None


_profile_hint = re.compile(
    r"\b(profile|team|staff|about|bio|cv|vitae|faculty|author|speaker)\b", re.I
)

def find_profile_by_email_nonlinkedin(email: str, top_k: int = 10) -> Optional[Dict]:
    q = f'"{email}" -site:linkedin.com'
    for r in smart_search_html(q, top_k):
        if "linkedin.com" in r["link"]:
            continue
        blob = (r["title"] + " " + r["snippet"]).lower()
        if _profile_hint.search(blob):
            return r
    return None

if __name__ == "__main__":
    # print("1) Name → LinkedIn")
    # print(find_linkedin_by_name("Jan‑Eike", "Andresen"))

    # print("\n2) Email → LinkedIn")
    # print(find_linkedin_by_email("anwari@rosepartner.de"))

    print("\n2) Email → LinkedIn")
    print(find_linkedin_by_email("andresen@rosepartner.de"))

    # print("\n3) Email → non‑LinkedIn profile page")
    # pprint(find_profile_by_email_nonlinkedin("andresen@rosepartner.de"))
