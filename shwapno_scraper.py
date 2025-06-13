import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import json
import os

# --- Google Sheets Configuration ---
# Google Service Account Key (as a string from GitHub Secret or env var)
# This will be loaded from an environment variable in GitHub Actions
GOOGLE_SERVICE_ACCOUNT_KEY_JSON = os.environ.get('GSPREAD_SERVICE_ACCOUNT_KEY')

# Google Sheet Name and Worksheet Name
SPREADSHEET_NAME = 'Shwapno Grocery Data' # আপনার গুগল শিটের নাম
WORKSHEET_NAME = 'Products'              # আপনার ওয়ার্কশিটের নাম

# --- Scraping Configuration ---
BASE_URL = "https://www.shwapno.com"
# যদি একটি নির্দিষ্ট পণ্যের পেজ স্ক্র্যাপ করতে চান:
# CATEGORY_URL = "https://www.shwapno.com/product/aci-pure-fortified-jeerashail-rice-5kg-14227"
# যদি ক্যাটাগরি পেজ থেকে একাধিক পণ্য স্ক্র্যাপ করতে চান (যেমন 'চাউল' ক্যাটাগরি):
CATEGORY_URL = "https://www.shwapno.com/eggs" # উদাহরণস্বরূপ, চাউলের ক্যাটাগরি। আপনি এটি পরিবর্তন করতে পারেন।
MAX_PAGES = 1 # কতগুলো পেজ স্ক্র্যাপ করতে চান। সতর্কতার সাথে এই সংখ্যা বাড়ান।

def get_soup(url):
    """Fetches the URL and returns a BeautifulSoup object."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
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

    # এখানে আপনাকে স্বপ্নের বর্তমান HTML অনুযায়ী সঠিক সিলেক্টর ব্যবহার করতে হবে
    # যদি এটি একটি ক্যাটাগরি পেজ হয়, যেখানে অনেকগুলো পণ্যের কার্ড আছে:
    # প্রতিটি পণ্যের কার্ডকে ধারণ করা div/tag খুঁজে বের করুন।
    # আমি এখন একটি সাধারণ 'product-card' বা 'product-item' ক্লাস অনুমান করছি
    # আপনাকে Inspect Element করে সঠিক ক্লাসটি খুঁজে বের করতে হবে।
    
    # শপ্নের ক্যাটাগরি পেজে product-card না থাকতে পারে।
    # সম্ভবত <div class="w-full flex-shrink-0 relative"> এর মধ্যে individual products থাকে
    # অথবা <div class="col-6 col-lg-3"> এরকম কিছু।
    # আমি একটি সম্ভাব্য জেনেরিক কন্টেইনার ক্লাস ব্যবহার করছি, যা আপনাকে পরিবর্তন করতে হতে পারে।
    
    # প্রথমত, যাচাই করুন আপনি একটি সিঙ্গেল প্রোডাক্ট পেজ নাকি ক্যাটাগরি পেজ স্ক্র্যাপ করছেন
    # যদি CATEGORY_URL একটি সিঙ্গেল প্রোডাক্ট URL হয়, তাহলে product_cards খোঁজার দরকার নেই।
    if "/product/" in url: # If it's a single product page
        product_name_tag = soup.find('h1', id='product-name')
        price_tag = soup.find('ins', class_='inline-block') # এই ক্লাসটি price-এর জন্য ইউনিক মনে হচ্ছে
        amount_tag = soup.find('span', class_='whitespace-nowrap') # এই ক্লাসটি amount-এর জন্য ইউনিক মনে হচ্ছে

        name = product_name_tag.get_text(strip=True) if product_name_tag else 'N/A'
        price = price_tag.get_text(strip=True) if price_tag else 'N/A'
        amount = amount_tag.get_text(strip=True) if amount_tag else 'N/A'
        
        products_data.append([name, price, amount])
        print(f"Found on single product page: {name}, {price}, {amount}")
    
    else: # If it's a category page with multiple products
        # আপনাকে এখানে ক্যাটাগরি পেজে প্রতিটি পণ্যকে ধারণ করে এমন সঠিক কন্টেইনার ক্লাসটি খুঁজে বের করতে হবে।
        # উদাহরণস্বরূপ, এটি 'product-grid-item', 'col-lg-3', 'product-wrapper' ইত্যাদি হতে পারে।
        # আমি একটি জেনেরিক নাম দিচ্ছি, আপনাকে এটি পরিবর্তন করতে হবে।
        product_containers = soup.find_all('div', class_='product-item-container') # এটি একটি অনুমান। আপনাকে সঠিক ক্লাস খুঁজতে হবে।
        
        # যদি উপরেরটি কাজ না করে, শপ্নের ক্যাটাগরি পেজে প্রোডাক্ট লিস্টের কাঠামো কেমন তা দেখতে হবে।
        # সম্ভবত <div class="col-6 col-lg-3"> এর মধ্যে প্রতিটি প্রোডাক্ট থাকে।
        if not product_containers:
            product_containers = soup.find_all('div', class_='col-6') # আরেকটি অনুমান, col-6 একটি সাধারণ বুটস্ট্র্যাপ ক্লাস
            print(f"No specific 'product-item-container' found. Trying 'col-6' on {url}. Found {len(product_containers)} containers.")
        
        if not product_containers:
            print(f"No product containers found on {url}. Please inspect the HTML for category pages.")
            return []


        for container in product_containers:
            # এখন প্রতিটি কন্টেইনারের মধ্যে product name, price, amount খুঁজতে হবে।
            # যেহেতু এই তথ্যগুলো product-card এর মধ্যে আছে, তাহলে আমরা ওই কন্টেইনারের মধ্যে তাদের খুঁজতে পারি।
            # product name: এটি একটি h1 id="product-name" কিন্তু category page এ এটি h2 বা div হতে পারে।
            # আপনাকে প্রতিটি product container এর ভেতরের HTML inspect করে দেখতে হবে।
            
            # আমি এখানে ধরে নিচ্ছি যে এই কন্টেইনারের মধ্যে product name, price, amount সরাসরি থাকবে।
            # কিন্তু ক্যাটাগরি পেজে সম্ভবত এই সিলেক্টরগুলো ভিন্ন হবে।
            # Category page-এ সম্ভবত পণ্যের নাম <h2 class="product-title-class"> এর মধ্যে থাকে
            # এবং price <span class="price-amount-class"> এর মধ্যে থাকে।
            
            # এই অংশটি আপনাকে ক্যাটাগরি পেজের জন্য বিশেষভাবে কাস্টমাইজ করতে হবে।
            # নিচের লাইনগুলো সাধারণ ক্যাটাগরি পেজ স্ক্র্যাপিংয়ের জন্য আরও সম্ভাব্য:
            name_tag = container.find('a', class_='product-name') # অনুমান
            price_tag = container.find('span', class_='product-price') # অনুমান
            
            # ক্যাটাগরি পেজে 'amount' আলাদা করে নাও থাকতে পারে, সাধারণত '5kg' নামের অংশেই থাকে।
            # যদি থাকে, তাহলে তার ক্লাস খুঁজে বের করতে হবে।
            # amount_tag = container.find('span', class_='product-amount') # অনুমান

            name = name_tag.get_text(strip=True) if name_tag else 'N/A'
            price = price_tag.get_text(strip=True) if price_tag else 'N/A'
            # amount = amount_tag.get_text(strip=True) if amount_tag else 'N/A' # যদি না পান, N/A রাখুন
            amount = 'N/A' # ক্যাটাগরি পেজে এটি আলাদাভাবে না থাকলে N/A রাখুন।

            products_data.append([name, price, amount])
            # print(f"Found: {name}, {price}, {amount}") # ডিবাগিং এর জন্য

    return products_data

# ... (বাকি কোড একই থাকবে, যেমন get_next_page_url, setup_google_sheets, main ফাংশনগুলো)
# তবে get_next_page_url ফাংশনটিও ক্যাটাগরি পেজের পেজিনেশন অনুযায়ী অ্যাডজাস্ট করতে হবে।
# আপনার দেওয়া ইনফরমেশন অনুসারে get_next_page_url ঠিক আছে যদি পেজিনেশন লিঙ্কগুলো একই রকম হয়।

def get_next_page_url(soup, current_page_num):
    """Finds the URL for the next page based on Shwapno's common pagination."""
    # Shwapno.com এর পেজিনেশন লিঙ্ক সাধারণত এরকম হয়:
    # <a href="/category/fresh-fish?page=2" class="page-link">2</a>
    # এটি পরের পেজের নম্বর যুক্ত লিঙ্ক খুঁজে বের করার চেষ্টা করবে।
    next_page_element = soup.find('a', string=str(current_page_num + 1), class_='page-link')
    if next_page_element and next_page_element.has_attr('href'):
         return BASE_URL + next_page_element['href']
    
    # যদি 'rel="next"' অ্যাট্রিবিউট সহ লিঙ্ক থাকে, তবে সেটিও চেক করা যেতে পারে।
    # next_page_link = soup.find('a', {'rel': 'next'})
    # if next_page_link and next_page_link.has_attr('href'):
    #     return BASE_URL + next_page_link['href']

    print(f"No more pages or specific next page link found after page {current_page_num}.")
    return None


def setup_google_sheets():
    """Authenticates with Google Sheets using service account."""
    if not GOOGLE_SERVICE_ACCOUNT_KEY_JSON:
        raise ValueError("GSPREAD_SERVICE_ACCOUNT_KEY environment variable is not set.")

    try:
        # Parse the JSON string from the environment variable
        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY_JSON)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error setting up Google Sheets client: {e}")
        raise

def main():
    all_products = []
    current_url = CATEGORY_URL
    page_num = 1

    print("Starting scraping...")
    # যদি সিঙ্গেল প্রোডাক্ট পেজ স্ক্র্যাপ করেন, তাহলে লুপের দরকার নেই।
    if "/product/" in CATEGORY_URL:
        all_products = scrape_page(CATEGORY_URL)
        current_url = None # Stop after single page
    else:
        while current_url and page_num <= MAX_PAGES:
            print(f"Scraping page {page_num}: {current_url}")
            products_on_page = scrape_page(current_url)
            all_products.extend(products_on_page)

            # নেক্সট পেজ লিঙ্ক খুঁজে বের করা
            soup_for_pagination = get_soup(current_url)
            if not soup_for_pagination:
                break
            
            current_url = get_next_page_url(soup_for_pagination, page_num)
            
            page_num += 1
            time.sleep(2) # Be polite to the server

    print(f"Finished scraping. Total products found: {len(all_products)}")

    if not all_products:
        print("No products were scraped. Exiting.")
        return

    print("Connecting to Google Sheets...")
    try:
        client = setup_google_sheets()
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        print(f"Connected to '{SPREADSHEET_NAME}' - '{WORKSHEET_NAME}'")

        # Clear existing data (optional, for fresh run)
        # worksheet.clear() # সাবধানে ব্যবহার করুন! এটি পুরো শিট মুছে দেবে।

        # Add headers if the sheet is empty
        if worksheet.row_count < 1 or not worksheet.row_values(1):
             worksheet.append_row(['Product Name', 'Price', 'Amount/Unit']) # Header updated

        # Append data
        worksheet.append_rows(all_products)
        print(f"Successfully appended {len(all_products)} products to Google Sheet.")

    except Exception as e:
        print(f"Failed to write to Google Sheet: {e}")

if __name__ == "__main__":
    main()
