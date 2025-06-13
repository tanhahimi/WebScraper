import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import json
import os

# --- Google Sheets Configuration ---
GOOGLE_SERVICE_ACCOUNT_KEY_JSON = os.environ.get('GSPREAD_SERVICE_ACCOUNT_KEY')
SPREADSHEET_NAME = 'Shwapno Grocery Data'
WORKSHEET_NAME = 'Products'

# --- Scraping Configuration ---
BASE_URL = "https://www.shwapno.com"
CATEGORY_URL = "https://www.shwapno.com/aci-pure-fortified-jeerashail-rice-5kg-6" # উদাহরণস্বরূপ, প্যাকিং রাইসের ক্যাটাগরি। আপনি এটি পরিবর্তন করতে পারেন।
MAX_PAGES = 3

def get_soup(url):
    """Fetches the URL and returns a BeautifulSoup object."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def scrape_page(url):
    """Scrapes product data from a single page."""
    soup = get_soup(url)
    if not soup:
        return []

    products_data = []

    # --- THIS IS THE CRUCIAL PART TO UPDATE BASED ON YOUR INSPECTION ---
    # You need to find the HTML element that acts as a container for EACH individual product.
    # Look for a div or similar tag that wraps the image, name, price, and amount.
    # Common examples: <div class="product-item-container">, <div class="col-6">, <div class="product-card">
    # Replace 'YOUR_PRODUCT_CONTAINER_CLASS' with the actual class you find.

    # Example: If each product is inside a div with class 'product-card-wrapper'
    product_containers = soup.find_all('div', class_='overflow-hidden text-ellipsis text-center text-xs font-normal leading-1 text-[#222] md:text-sm lg:font-medium active:outline-dotted active:outline-1 line-clamp-1 md:leading-5') # <--- YOU MUST UPDATE THIS LINE!
                                                                                # e.g., 'product-card-wrapper' or 'product-grid-item'
                                                                                # or 'col-6 col-lg-3' depending on the exact structure.
                                                                                # Check this on https://www.shwapno.com/packed-rice

    if not product_containers:
        print(f"No product containers found with the specified class on {url}.")
        print("Please inspect the HTML of the category page to find the correct class for product containers.")
        return []

    for container in product_containers:
        # Product Name
        name_tag = container.find('a', class_='overflow-hidden') # Found in your example
        name = name_tag.get_text(strip=True) if name_tag else 'N/A'

        # Price
        price_tag = container.find('span', class_='active-price') # Found in your example
        price = price_tag.get_text(strip=True) if price_tag else 'N/A'

        # Amount / Unit
        # The span for amount doesn't have a unique class, so we look for a generic span that contains the unit info.
        # This might need refinement if other spans also match.
        # You could also find all spans and check their text, or find the span immediately following the price.
        amount_tag = container.find('span', class_='text-[#3c3e44]') # Based on your example class structure
        # Or, if this specific class isn't unique, you might need to find all spans and filter:
        # all_spans = container.find_all('span')
        # amount = 'N/A'
        # for s in all_spans:
        #    if 'Per Piece' in s.get_text() or 'kg' in s.get_text() or 'g' in s.get_text():
        #        amount = s.get_text(strip=True)
        #        break

        amount = amount_tag.get_text(strip=True) if amount_tag else 'N/A'
        # Clean up the amount string (e.g., remove leading '&nbsp;')
        amount = amount.replace('\xa0', ' ').strip() # \xa0 is non-breaking space

        products_data.append([name, price, amount])
        # print(f"Found: Name: {name}, Price: {price}, Amount: {amount}") # For debugging

    return products_data

# ... (rest of the code for get_next_page_url, setup_google_sheets, main function remains the same)

# The get_next_page_url and main functions from the previous response are still valid.
# Just make sure to correctly identify 'YOUR_PRODUCT_CONTAINER_CLASS' by inspecting the category page.
