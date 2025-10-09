from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

import time

url = "https://msu.io/marketplace/nft"

# --- Setup Chrome Options ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
# Optional: Add a custom User-Agent to mimic a real browser more closely
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# --- Use webdriver-manager to automatically handle ChromeDriver ---
service = Service(ChromeDriverManager().install())

driver = None
try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)

    # --- Wait for page to load and add some debugging ---
    print("Waiting for page to load...")
    time.sleep(5)  # Give the page time to load
    
    # Try to find any common elements instead of specific class
    try:
        # Wait for body to be present (basic check)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("Page body loaded successfully")
    except Exception as e:
        print(f"Timeout waiting for page to load: {e}")
        # Continue anyway to see what we can get

    print(f"Page title: {driver.title}")
    print(f"Current URL: {driver.current_url}")

    # --- Get the page source and extract NFT data ---
    page_source = driver.page_source
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Extract NFT names and prices
    nft_names = soup.find_all(class_="BaseCard_itemName__Z2GfD")
    nft_prices = soup.find_all(class_="CardPrice_number__OYpdb")
    
    print(f"Found {len(nft_names)} NFT names and {len(nft_prices)} prices")
    
    # Display the NFT data
    for i, (name, price) in enumerate(zip(nft_names, nft_prices)):
        print(f"NFT {i+1}:")
        print(f"  Name: {name.get_text().strip()}")
        print(f"  Price: {price.get_text().strip()}")
        print()
    
    # If no data found, let's see what classes are available
    if len(nft_names) == 0 or len(nft_prices) == 0:
        print("No NFT data found with those classes. Let's check what's available:")

        # Check for any elements that might contain price-like data or item names
        all_text_elements = soup.find_all(['div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
        price_like_elements = []
        for elem in all_text_elements:
            text = elem.get_text().strip()
            # Look for text that might be prices (contain numbers and $ or specific formats)
            if any(char.isdigit() for char in text):
                if len(text) < 20:  # Reasonable length for price
                    price_like_elements.append((elem.get('class'), text))

        print(f"Found {len(price_like_elements)} possible price elements:")
        for i, (classes, text) in enumerate(price_like_elements[:10]):
            print(f"  {i+1}. Classes: {classes} - Text: '{text}'")

        # Look for item name-like elements
        name_like_elements = []
        for elem in all_text_elements:
            text = elem.get_text().strip()
            if (2 <= len(text.split()) <= 5 and  # Reasonable word count for item names
                not any(char.isdigit() for char in text[:5]) and  # Not starting with numbers
                len(text) > 3):  # Longer than just symbols
                name_like_elements.append((elem.get('class'), text))

        print(f"\nFound {len(name_like_elements)} possible item name elements:")
        for i, (classes, text) in enumerate(name_like_elements[:10]):
            print(f"  {i+1}. Classes: {classes} - Text: '{text}'")

        # Save page source for manual inspection
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("\n💾 Saved page source to 'page_source.html' for manual inspection")

        # Let's also check for any elements containing "Card" or "Price"
        card_elements = soup.find_all(class_=lambda x: x and any('card' in cls.lower() or 'price' in cls.lower() for cls in x))
        print(f"\nFound {len(card_elements)} elements with 'card' or 'price' in class name:")
        for elem in card_elements[:5]:  # Show first 5
            print(f"  Class: {elem.get('class')} - Text: {elem.get_text().strip()[:50]}...")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if driver:
        driver.quit() # Always close the browser
