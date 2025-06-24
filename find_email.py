import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def find_emails(url,
                timeout,
                user_agent = "Mozilla/5.0 (compatible; EmailHunter/1.0)"):
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[warn] Cannot fetch {url}: {exc}")
        return []

    return find_emails_content(resp.text)

def find_emails_content(url, content):

    seen = set()
    
    soup = BeautifulSoup(content, 'lxml')

    seen.update(map(str.lower, EMAIL_RE.findall(content)))

    snippets = list(soup.stripped_strings)
    for attr in ("alt", "title", "aria-label"):
        snippets.extend(tag.get(attr) for tag in soup.find_all(attrs={attr: True}))

    snippets.extend(
        a["href"].split(":", 1)[1]
        for a in soup.find_all("a", href=True)
        if a["href"].lower().startswith("mailto:")
    )

    for text in snippets:
        seen.update(map(str.lower, EMAIL_RE.findall(text or "")))

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".vcf"):
            vcf_url = urljoin(url, href)
            try:
                vcf_resp = requests.get(vcf_url)
                vcf_resp.raise_for_status()
                vcf_text = vcf_resp.text
                seen.update(map(str.lower, EMAIL_RE.findall(vcf_text)))
            except requests.RequestException as e:
                print(f"[warn] Failed to fetch .vcf file {vcf_url}: {e}")

    return seen
