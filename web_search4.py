import time, random, re, html, urllib.parse, requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from pprint import pprint
def find_links_by_email(email: str, max_results=5) -> list:
    query = email.strip()
    results = []

    # SearXNG (adjust to working instance)
    url = "https://searx.tiekoetter.com/search"
    params = {
        "q": query,
        "format": "json",
        "engines": "google,duckduckgo,bing",
        "language": "en",
        "safesearch": "0"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        for item in r.json().get("results", [])[:max_results]:
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content")
            })
    except Exception as e:
        print("Search failed:", e)

    return results

email = "anwari@rosepartner.de"
for r in find_links_by_email(email):
    print(r["title"], "=>", r["url"])
