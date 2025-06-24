
from analyse_website_email import resolve_person_links
from crawl_website import find_all_pages
from handle_excel_sheets import get_email_links, read_sheets_file, update_email_links_data, update_email_person_data, update_website_data

if __name__ == '__main__':
    sheets_file = input("Enter .XLSX file to read: ")
    print(f'READING:  {sheets_file}')
    workbook, websites_dict, emails_dict = read_sheets_file(sheets_file)
    print(f'WEBSITES FOUND: {len(list(websites_dict.keys()))}')
    print(f'EMAILS FOUND: {len(list(emails_dict.keys()))}')

    print("STEP 1 - finding links and emails on websites with no data")
    for website in websites_dict.keys():
        row = websites_dict[website]
        if row[1].value is None or len(row[1].value) == 0:
            print(f"Processing website: {website}")
            pages, emails = find_all_pages(website)
            print(f"Found {len(pages)} pages and {len(emails)} emails on {website}")
            update_website_data(workbook, websites_dict, website, pages, list(emails.keys()))
            for email in emails.keys():
                links = emails[email]
                update_email_links_data(workbook, emails_dict, email, list(links))

            workbook.save(sheets_file)

    print("STEP 2 - finding info on emails")
    for email in emails_dict.keys():
        row = emails_dict[email]
        if row and (row[1] is None or row[1].value is None or len(row[1].value) == 0):
            print(f"Processing email: {email}")
            links = get_email_links(emails_dict, email)
            best_details = resolve_person_links(email, links)
            update_email_person_data(workbook, emails_dict, email, best_details)

            workbook.save(sheets_file)

    workbook.save(sheets_file)
    print(f"Data saved to {sheets_file}")