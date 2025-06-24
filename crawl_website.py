import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import re
import time
from find_email import find_emails_content

def remove_repeated_segments(url):
    parsed = urlparse(url)
    segments = parsed.path.split('/')
    normalized_segments = []
    
    for segment in segments:
        if segment and (not normalized_segments or segment != normalized_segments[-1]):
            normalized_segments.append(segment)
    normalized_path = '/'.join(normalized_segments)
    return parsed._replace(path=normalized_path).geturl()
def normalize_url(url):
    url = remove_repeated_segments(url)
    parsed_url = urlparse(url)
    path = parsed_url.path.rstrip('/').replace('.html', '')
    return f"{parsed_url.scheme}://{parsed_url.netloc}{path}".lower()

def is_valid_link(url, base_url):
    ignored_extensions = ('.webmanifest', '.png', '.svg', '.js', '.css', '.ico', '.jpg', '.jpeg', '.gif', '.pdf', '.vcf')
    return (not url.endswith(ignored_extensions) and 
            # 'blog' not in url and
            # '#' not in url and
            urlparse(url).netloc == base_url)

def add_link(url, base_url, links):
    normalized_url = normalize_url(url)
    if (is_valid_link(normalized_url, base_url)):
        links.add(normalized_url)
        return normalized_url
    return None

def find_all_links(url, content, content_type, base_url):
    
    links = set()

    soup = BeautifulSoup(content, 'lxml')

    for link in soup.find_all('a', href=True):
        full_url = urljoin(url, link['href'])
        add_link(full_url, base_url, links)

    if 'text' in content_type:
        try:
            decoded_content = content.decode('utf-8')
            hidden_links = re.findall(r'href=[\'"]?([^\'" >]+)', decoded_content)
            for hidden_link in hidden_links:
                full_url = urljoin(url, hidden_link)
                add_link(full_url, base_url, links)
        except (UnicodeDecodeError, TypeError):
            print(f"Could not decode content for {url}")
    return links
def add_emails(url, content_text, emails):
    new_emails = find_emails_content(url, content_text)
    for email in new_emails:
        if email not in emails:
            emails[email] = set()
        emails[email].add(url)

def find_all_pages(start_url):
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    start_url = start_url.lower()

    visited = set()
    emails = {}
    parts = urlparse(start_url)
    base_url = parts.netloc

    initial_url = f"{parts.scheme}://{base_url}"

    start_urls = [
        start_url,
        initial_url,
        urljoin(initial_url, 'home'),
        urljoin(initial_url, 'index'),
        urljoin(initial_url, 'sitemap'),
        urljoin(initial_url, 'sitemap_index')
    ]
    queue = deque(start_urls)

    start_time = time.time()

    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        page_start_time = time.time()
        content, content_text, content_type = fetch_page(url)
        page_end_time = time.time()
        print(f"Time taken to fetch {url}: {page_end_time - page_start_time:.2f} seconds")

        if content is None:
            continue

        links = find_all_links(url, content, content_type, base_url)
        for link in links:
            if (link not in visited):
                queue.append(link)

        add_emails(url, content_text, emails)

    end_time = time.time()
    pages = list(visited)
    print(f"Total time taken for crawling {len(pages)} pages: {end_time - start_time:.2f} seconds")
    print('emails: ')
    print(list(emails.keys()))

    return pages, emails

def fetch_page(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content, response.text, response.headers.get('Content-Type', '')
        return None, None, ''
    except requests.RequestException as e:
        return None, None, ''