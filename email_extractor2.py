import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def extract_name_from_email(email):
    """Attempts to extract a name from an email address."""
    # Common patterns: firstname.lastname@, firstnamelastname@, f.lastname@, firstname@
    match = re.match(r'([a-zA-Z0-9._%+-]+)@', email)
    if match:
        local_part = match.group(1)
        local_part = local_part.replace('.', ' ').replace('-', ' ').replace('_', ' ')
        names = [n.capitalize() for n in local_part.split() if n]
        
        first_name = names[0] if names else None
        last_name = names[-1] if len(names) > 1 else None
        
        return first_name, last_name
    return None, None

def identify_person_from_website(email, company_website_url):
    """Attempts to identify a person's details from a company website based on their email."""
    first_name, last_name = extract_name_from_email(email)
    person_details = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "position": None,
        "gender": None  # Gender identification is complex and often inaccurate without external APIs
    }

    if not first_name and not last_name:
        return person_details # Cannot proceed without at least a potential name

    search_terms = []
    if first_name and last_name:
        search_terms.append(f"{first_name} {last_name}")
        search_terms.append(f"{last_name}, {first_name}")
    elif first_name:
        search_terms.append(first_name)
    elif last_name:
        search_terms.append(last_name)

    # Common pages to search for people
    potential_paths = [company_website_url, 
                       urljoin(company_website_url, 'about'), 
                       urljoin(company_website_url, 'about-us'),
                       urljoin(company_website_url, 'team'), 
                       urljoin(company_website_url, 'our-team'),
                       urljoin(company_website_url, 'leadership'),
                       urljoin(company_website_url, 'contact'),
                       urljoin(company_website_url, 'contact-us')]

    for url in potential_paths:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            for term in search_terms:
                if term.lower() in page_text.lower():
                    # Found a potential name match on the page
                    # Now try to find a position near the name
                    # This is a very basic approach and can be improved
                    
                    # Look for text around the name
                    context_window = 200 # characters before and after the name
                    name_index = page_text.lower().find(term.lower())
                    if name_index != -1:
                        start = max(0, name_index - context_window)
                        end = min(len(page_text), name_index + len(term) + context_window)
                        context = page_text[start:end]

                        # Simple regex to find common job titles in the context
                        # This list can be expanded significantly
                        job_title_patterns = [
                            r'\b(CEO|CTO|CFO|CMO|COO|President|Vice President|VP|Director|Manager|Head of|Lead|Engineer|Developer|Specialist|Analyst|Consultant|Administrator|Coordinator|Officer)\b',
                            r'\b(Software Engineer|Project Manager|Marketing Manager|Sales Manager|HR Manager|Accountant)\b'
                        ]
                        for pattern in job_title_patterns:
                            job_match = re.search(pattern, context, re.IGNORECASE)
                            if job_match:
                                person_details["position"] = job_match.group(0)
                                break
                    
                    # Update first and last name with the found capitalized version if available
                    if first_name and last_name:
                        person_details["first_name"] = term.split()[0].capitalize()
                        person_details["last_name"] = term.split()[-1].capitalize()
                    elif first_name:
                        person_details["first_name"] = term.capitalize()
                    elif last_name:
                        person_details["last_name"] = term.capitalize()

                    return person_details # Return as soon as a match is found

        except requests.exceptions.RequestException as e:
            # print(f"Error accessing {url}: {e}")
            pass # Silently fail for now, as many paths might not exist

    return person_details

def extract_emails(url):
    unique_emails = set()
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return unique_emails

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find emails in mailto links
    for link in soup.find_all('a', href=True):
        if 'mailto:' in link['href']:
            email = link['href'].replace('mailto:', '')
            unique_emails.add(email)

    # Find emails in plain text using regex
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}')
    for match in re.finditer(email_pattern, response.text):
        unique_emails.add(match.group(0))

    return unique_emails

def crawl_and_extract_emails(base_url):
    all_emails = set()
    crawled_urls = set()
    to_crawl = [base_url]
    
    # Define common contact-related paths
    contact_paths = ['/contact', '/about', '/team', '/info', '/contact-us', '/about-us']

    while to_crawl and len(crawled_urls) < 20:  # Limit crawling depth for practical purposes
        current_url = to_crawl.pop(0)
        if current_url in crawled_urls:
            continue

        print(f"Crawling: {current_url}")
        crawled_urls.add(current_url)

        # Extract emails from the current page
        emails_on_page = extract_emails(current_url)
        all_emails.update(emails_on_page)

        # Find internal links to crawl further, especially contact-related ones
        try:
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                
                # Only follow links within the same domain
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    # Prioritize contact-related pages
                    if any(path in href.lower() for path in contact_paths) and full_url not in crawled_urls:
                        to_crawl.insert(0, full_url) # Add to front to prioritize
                    elif full_url not in crawled_urls:
                        to_crawl.append(full_url)
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {current_url} for links: {e}")

    return all_emails

if __name__ == '__main__':
    print("Choose an option:")
    print("1. Extract emails from a website")
    print("2. Identify person from an email and website")
    print("3. Extract emails and identify persons from a website (all-in-one)")
    choice = input("Enter your choice (1, 2, or 3): ")

    if choice == '1':
        company_website = input("Enter the company website URL (e.g., https://example.com): ")
        if not company_website.startswith(('http://', 'https://')):
            company_website = 'https://' + company_website

        print(f"\nSearching for emails on {company_website}...")
        found_emails = crawl_and_extract_emails(company_website)

        if found_emails:
            print("\nFound Emails:")
            for email in sorted(list(found_emails)):
                print(email)
        else:
            print("\nNo publicly available emails found.")

    elif choice == '2':
        test_email = input("Enter an email address (e.g., john.doe@example.com): ")
        test_website = input("Enter the company website URL (e.g., https://example.com): ")
        if not test_website.startswith(("http://", "https://")):
            test_website = "https://" + test_website

        details = identify_person_from_website(test_email, test_website)
        print("\nIdentified Person Details:")
        for key, value in details.items():
            print(f"{key.replace('_', ' ').capitalize()}: {value}")

    elif choice == '3':
        company_website = input("Enter the company website URL (e.g., https://example.com): ")
        if not company_website.startswith(('http://', 'https://')):
            company_website = 'https://' + company_website

        print(f"\nSearching for emails and identifying persons on {company_website}...")
        found_emails = crawl_and_extract_emails(company_website)

        if found_emails:
            print("\nFound Emails and Identified Persons:")
            for email in sorted(list(found_emails)):
                person_details = identify_person_from_website(email, company_website)
                print(f"\nEmail: {person_details['email']}")
                print(f"  First Name: {person_details['first_name']}")
                print(f"  Last Name: {person_details['last_name']}")
                print(f"  Position: {person_details['position']}")
        else:
            print("\nNo publicly available emails found.")

    else:
        print("Invalid choice. Please run the script again and enter 1, 2, or 3.")


