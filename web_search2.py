import time, random, re, html, requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

session = requests.Session()

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/125.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://google.com/",
}

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

def _searx_html(query: str, n: int) -> List[Dict]:
    params = {
        "q": query,
        "engines": "google,bing,duckduckgo",
        "language": "en",
        "safesearch": 1,
        "categories": "general",
        "time_range": 365,
    }
    for base in SEARXNG_URLS:
        try:
            resp = session.get(f"{base}/search", params=params, headers=BASE_HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            out = []
            for res in soup.select("div.result")[:n]:
                a = res.select_one("h3 > a, a.result__a, a")
                if not a or not a.get("href"):
                    continue
                snip = res.select_one(".content") or res.select_one("p")
                out.append({
                    "title": a.get_text(" ", strip=True),
                    "link": a["href"],
                    "snippet": snip.get_text(" ", strip=True) if snip else ""
                })
            if out:
                return out
        except Exception:
            time.sleep(1)
    return []

def _google_html(query: str, n: int) -> List[Dict]:
    try:
        resp = session.get("https://www.google.com/search",
                           params={"q": query, "num": n},
                           headers=BASE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for g in soup.select(".tF2Cxc")[:n]:
            a = g.select_one("a[href]")
            h3 = g.select_one("h3")
            snip = g.select_one(".VwiC3b") or g.select_one(".aCOpRe")
            if not a or not h3:
                continue
            out.append({
                "title": h3.get_text(" ", strip=True),
                "link": a["href"],
                "snippet": snip.get_text(" ", strip=True) if snip else ""
            })
        return out
    except Exception:
        return []

def _duckduckgo_html(query: str, n: int) -> List[Dict]:
    try:
        resp = session.post("https://duckduckgo.com/html/",
                            data={"q": query},
                            headers=BASE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for res in soup.select(".result")[:n]:
            a = res.select_one("a.result__a")
            snip = res.select_one(".result__snippet")
            if not a:
                continue
            link = html.unescape(a["href"])
            out.append({
                "title": a.get_text(" ", strip=True),
                "link": link,
                "snippet": snip.get_text(" ", strip=True) if snip else ""
            })
        return out
    except Exception:
        return []
def _presearch_html(query: str, n: int) -> List[Dict]:
    try:
        resp = session.post("https://presearch.com/search",
                            data={"q": query},
                            headers=BASE_HEADERS, timeout=15)
        resp.raise_for_status()
        print("PRESEARCH RESULT:")
        print(resp.text)
        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for res in soup.select(".result")[:n]:
            a = res.select_one("a.result__a")
            snip = res.select_one(".result__snippet")
            if not a:
                continue
            link = html.unescape(a["href"])
            out.append({
                "title": a.get_text(" ", strip=True),
                "link": link,
                "snippet": snip.get_text(" ", strip=True) if snip else ""
            })
        return out
    except Exception:
        print("PRESEARCH ERROR")
        return []

def _bing_html(query: str, n: int) -> List[Dict]:
    try:
        resp = session.get("https://www.bing.com/search",
                           params={"q": query, "count": n},
                           headers=BASE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        out = []
        for li in soup.select("li.b_algo")[:n]:
            a = li.select_one("a[href]")
            snip = li.select_one(".b_caption p")
            if not a:
                continue
            out.append({
                "title": a.get_text(" ", strip=True),
                "link": a["href"],
                "snippet": snip.get_text(" ", strip=True) if snip else ""
            })
        return out
    except Exception:
        return []

def smart_search(query: str, num: int = 6) -> List[Dict]:
    all_results = []

    for engine in (_searx_html, _duckduckgo_html, _presearch_html, _google_html):
    # for engine in (_searx_html, _duckduckgo_html, _google_html, _bing_html):
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


def find_linkedin_by_name(first: str, last: str, top_k: int = 6) -> Optional[str]:
    q = f'"{first} {last}" site:linkedin.com/in'
    for r in smart_search(q, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


def find_linkedin_by_email(email: str, top_k: int = 20) -> Optional[str]:
    # q = f'"{email}" site:linkedin.com/in'
    q = f'"{email}"'
    for r in smart_search(q, top_k):
        print(r["link"])
        # if "linkedin.com/in/" in r["link"]:
            # return r["link"]
    return None


_profile_hint = re.compile(
    r"\b(profile|team|staff|about|bio|cv|vitae|faculty|author|speaker)\b", re.I
)

def find_profile_by_email_nonlinkedin(email: str, top_k: int = 10) -> Optional[Dict]:
    q = f'"{email}" -site:linkedin.com'
    for r in smart_search(q, top_k):
        if "linkedin.com" in r["link"]:
            continue
        blob = (r["title"] + " " + r["snippet"]).lower()
        if _profile_hint.search(blob):
            return r
    return None

# print(find_linkedin_by_name("Jan‑Eike", "Andresen"))
# print(find_linkedin_by_email("anwari@rosepartner.de"))
print(find_linkedin_by_email("andresen@rosepartner.de"))
# pprint(find_profile_by_email_nonlinkedin("andresen@rosepartner.de"))