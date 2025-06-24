
from __future__ import annotations
import time, urllib.parse, re, sys
from typing import List, Dict, Optional
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

# ─────────────────────────────── driver factory ─────────────────────────
def make_driver(headless: bool = True):
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-US,en")

    opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # macOS

    return uc.Chrome(options=opts)

# ─────────────────────────── core search routine ────────────────────────
def google_search_html(query: str, num: int = 10) -> List[Dict]:
    """
    Perform a Google search via undetected‑chromedriver and return a list of
    {title, link, snippet} dicts (up to *num* results).
    """
    q = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={q}&num={num}&hl=en"

    driver = make_driver(headless=True)
    try:
        driver.get(url)
        time.sleep(1.5)           # small wait for JS, ads, etc.

        soup = BeautifulSoup(driver.page_source, "html.parser")
        results = []
        for blk in soup.select(".tF2Cxc"):
            a = blk.select_one("a")
            h3 = blk.select_one("h3")
            snippet = blk.select_one(".VwiC3b") or blk.select_one(".aCOpRe")
            if a and h3:
                results.append({
                    "title": h3.get_text(" ", strip=True),
                    "link": a["href"],
                    "snippet": snippet.get_text(" ", strip=True) if snippet else ""
                })
            if len(results) >= num:
                break
        return results
    finally:
        driver.quit()

# ───────────────────────── task‑level helpers ───────────────────────────
def find_linkedin_by_name(first: str, last: str, top_k: int = 8) -> Optional[str]:
    query = f'"{first} {last}" site:linkedin.com/in'
    for r in google_search_html(query, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


def find_linkedin_by_email(email: str, top_k: int = 8) -> Optional[str]:
    query = f'"{email}" site:linkedin.com/in'
    for r in google_search_html(query, top_k):
        if "linkedin.com/in/" in r["link"]:
            return r["link"]
    return None


_PROFILE_HINT = re.compile(
    r"\b(profile|team|staff|about|bio|cv|vitae|faculty|author|speaker)\b", re.I
)

def find_profile_by_email_nonlinkedin(email: str, top_k: int = 10) -> Optional[str]:
    # query = f'"{email}" -site:linkedin.com'
    query = f'"{email}"'
    for r in google_search_html(query, top_k):
        # if "linkedin.com" in r["link"]:
        #     continue
        blob = (r["title"] + " " + r["snippet"]).lower()
        if email in blob:
        # if _PROFILE_HINT.search(blob):
            return r["link"]
    return None


# ───────────────────────────── example run ──────────────────────────────
if __name__ == "__main__":
    # print("🔎  Email → LinkedIn")
    # print(find_linkedin_by_email("anwari@rosepartner.de"))

    # print("\n🔎  Name  → LinkedIn")
    # print(find_linkedin_by_name("Jan‑Eike", "Andresen"))

    print("\n🔎  Email → non‑LinkedIn profile")
    print(find_profile_by_email_nonlinkedin("andresen@rosepartner.de"))
