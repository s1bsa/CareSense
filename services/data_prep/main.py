import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

# Define the permissions scope
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# Connect to Google Sheets
client = gspread.authorize(creds)

# Open your spreadsheet
spreadsheet = client.open("caresense_data")
sheet = spreadsheet.sheet1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_link(disease_name):
    result = search_cleveland(disease_name)

    if result is None:
        result = search_nhs(disease_name)

    # If still no match, try again without 'acute' prefix
    if result is None and disease_name.strip().lower().startswith("acute "):
        stripped_name = disease_name.strip().lower().replace("acute ", "", 1).strip()
        result = search_cleveland(stripped_name)

    return result

def scrape_cleve(url):
    """Visit Cleveland Clinic page once and extract both summary and tests."""
    print(f"Scraping: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()

    # --- Summary ---
    summary = "N/A"
    for heading in soup.find_all(["h2", "h3"]):
        if heading.get_text(strip=True).lower().startswith("what is"):
            for p in heading.find_all_next("p"):
                text = p.get_text(separator=" ", strip=True)
                if (len(text) > 100
                        and "this image is available" not in text.lower()
                        and "scassets/images" not in text.lower()
                        and "view image" not in text.lower()):
                    summary = text
                    break
            break

    # --- Tests ---
    tests = "N/A"
    diagnosis_heading = None
    for heading in soup.find_all(["h2", "h3"]):
        if "diagnosis and tests" in heading.get_text(strip=True).lower():
            diagnosis_heading = heading
            break

    if diagnosis_heading:
        heading_tag = diagnosis_heading.name
        content = []
        for sibling in diagnosis_heading.find_next_siblings():
            if sibling.name == heading_tag:
                break
            for element in sibling.children:
                text = element.get_text(separator=" ", strip=True) if hasattr(element, 'get_text') else str(element).strip()
                if text.strip():
                    content.append(text.strip())
        tests = " ".join(content) if content else "N/A"

    return summary, tests


def search_cleveland(name):
    print("Searching Cleveland...")
    cleaned_name = name.strip().lower()
    query = cleaned_name.replace(" ", "%20")
    search_url = f"https://my.clevelandclinic.org/search?q={query}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="networkidle")
        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()

    links = soup.find_all("a", href=True)

    for link in links:
        href = link["href"]

        if "/health/diseases/" not in href:
            continue

        if href.startswith("/"):
            href = "https://my.clevelandclinic.org" + href

        article_title = link.get_text(strip=True)

        # Exact match
        if article_title.lower() == cleaned_name:
            return href

        # Fallback: compare without spaces
        if article_title.replace(" ", "").lower() == cleaned_name.replace(" ", ""):
            return href

        # Fallback: strip bracket suffix
        title_without_bracket = article_title.split("(")[0].strip()
        if title_without_bracket.replace(" ", "").lower() == cleaned_name.replace(" ", ""):
            return href

    return None

def search_nhs(name):
    print("Searching NHS...")
    cleaned_name = name.strip().lower()
    query = cleaned_name.replace(" ", "%20")
    search_url = f"https://www.nhs.uk/search/results?q={query}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="networkidle")
        page.wait_for_timeout(3000)
        links = page.locator("a")
        for i in range(links.count()):
            link = links.nth(i)

            href = link.get_attribute("href")
            title = link.inner_text().strip().lower()

            if href.startswith("/"):
                href = "https://www.nhs.uk" + href

            if cleaned_name in title:
                browser.close()
                return href
        browser.close()
    return None

def process_rows(start_row, end_row):
    all_rows = sheet.get_all_values()

    # Convert to 0-indexed for list access, offset by 2 for header
    for i in range(start_row, end_row + 1):
        row_index = i
        list_index = i + 2

        # Safety check
        if list_index >= len(all_rows):
            print(f"  ⚠️ Row {row_index} doesn't exist in sheet, stopping.")
            break

        row = all_rows[list_index]

        # Skip if column B is empty
        if len(row) < 2 or not row[1].strip():
            print(f"  Row {row_index}: skipping — column B is empty")
            continue

        disease_name = row[1].strip()
        print(f"  Row {row_index}: searching for '{disease_name}'...")

        try:
            url = get_link(disease_name)

            if url:
                if url.startswith("https://my.clevelandclinic"):
                    print(f"    ✅ Match found: {url} on Cleveland Clinic")
                    summary, tests = scrape_cleve(url)
                    sheet.update(range_name=f"J{row_index+3}", values=[[url]])
                    sheet.update(range_name=f"C{row_index+3}", values=[[summary]])
                    sheet.update(range_name=f"G{row_index + 3}", values=[[tests]])
                elif url.startswith("https://www.nhs.uk"):
                    print(f"    ✅ Match found: {url} on NHS website")
                    sheet.update(range_name=f"J{row_index + 3}", values=[[url]])
                    sheet.update(range_name=f"C{row_index + 3}", values=[["N/A"]])
                    sheet.update(range_name=f"G{row_index + 3}", values=[["N/A"]])
            else:
                print(f"    ❌ No match found — writing N/A")
                sheet.update(range_name=f"J{row_index+3}", values=[["N/A"]])
                sheet.update(range_name=f"C{row_index + 3}", values=[["N/A"]])
                sheet.update(range_name=f"G{row_index + 3}", values=[["N/A"]])

        except Exception as e:
            print(f"    ⚠️ Error: {e}")
            sheet.update(range_name=f"J{row_index+3}", values=[["ERROR"]])


        # Pause between requests to avoid being blocked
        time.sleep(2)

    print(f"\nDone! Processed rows {start_row} to {end_row}.")
    pass

process_rows(start_row=701, end_row=772)