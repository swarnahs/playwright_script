import json
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration
CREDENTIALS = {
    "username": "swarna.s.h@campusuvce.in",
    "password": "nvCkHjWe"
}
SESSION_FILE = "idenhq_session.json"
BASE_URL = "https://hiring.idenhq.com"
LOGIN_URL = f"{BASE_URL}/"
INSTRUCTIONS_URL = f"{BASE_URL}/instructions"
CHALLENGE_URL = f"{BASE_URL}/challenge"
OUTPUT_FILE = "products.json"

def save_session(storage_state):
    with open(SESSION_FILE, 'w') as f:
        json.dump(storage_state, f)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return None

def authenticate(page):
    print("Authenticating...")
    page.goto(LOGIN_URL)
    page.wait_for_selector('input[type="email"]', timeout=30000)
    page.fill('input[type="email"]', CREDENTIALS["username"])
    print("Entered email")
    page.fill('input[type="password"]', CREDENTIALS["password"])
    print("Entered password")
    page.click('button[type="submit"]')
    print("Clicked login button")
    try:
        page.wait_for_url(INSTRUCTIONS_URL, timeout=15000)
        print("Authentication successful")
        return page.context.storage_state()
    except PlaywrightTimeoutError:
        print("Authentication might have succeeded but didn't navigate to instructions")
        return page.context.storage_state()

def navigate_to_challenge(page):
    print("Navigating to challenge...")
    try:
        launch_button = page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
        launch_button.click()
        print("Clicked launch challenge")
        page.wait_for_url(CHALLENGE_URL, timeout=15000)
        print("Successfully navigated to challenge page")
        return True
    except PlaywrightTimeoutError:
        print("Could not find launch button or navigate to challenge")
        page.goto(CHALLENGE_URL)
        time.sleep(2)
        try:
            page.wait_for_selector('.grid > div', timeout=10000)
            print("Direct navigation to challenge succeeded")
            return True
        except PlaywrightTimeoutError:
            print("Direct navigation also failed")
            return False

def navigate_flippable_cards(page):
    print("Navigating through flippable cards to reveal product table...")
    page.wait_for_selector("#dashboard-card", timeout=30000)
    page.click("#dashboard-card")
    print("Clicked Dashboard card")
    page.wait_for_timeout(2000)  # wait 2 seconds for animation/loading

    page.wait_for_selector("#inventory-card", timeout=30000)
    page.click("#inventory-card")
    print("Clicked Inventory card")
    page.wait_for_timeout(2000)

    page.wait_for_selector("#catalog-card", timeout=30000)
    page.click("#catalog-card")
    print("Clicked Catalog card")
    page.wait_for_timeout(2000)

    page.wait_for_selector("button:has-text('View Complete Data')", timeout=30000)
    page.click("button:has-text('View Complete Data')")
    print("Clicked View Complete Data button")

    page.wait_for_selector("#product-table", timeout=30000)
    print("Product table is now visible")

def scroll_and_extract_products(page):
    print("Starting to scroll and extract products...")

    all_products = []
    seen_ids = set()
    scroll_attempts = 0
    max_scroll_attempts = 100
    no_new_products_count = 0

    while scroll_attempts < max_scroll_attempts:
        product_cards = page.query_selector_all('.grid > div')
        print(f"Found {len(product_cards)} product cards on page.")

        new_products = 0

        for card in product_cards:
            try:
                id_element = card.query_selector('p.font-mono')
                product_id = "N/A"
                if id_element:
                    id_text = id_element.inner_text().strip()
                    if 'ID:' in id_text:
                        product_id = id_text.split('ID:')[1].strip().split()[0]

                if product_id in seen_ids or product_id == "N/A":
                    continue
                seen_ids.add(product_id)
                new_products += 1

                name_element = card.query_selector('h3')
                name = name_element.inner_text().strip() if name_element else "N/A"

                category_element = card.query_selector('[class*="rounded-full"][class*="border"]')
                category = category_element.inner_text().strip() if category_element else "N/A"

                details = {"dimensions": "N/A", "color": "N/A", "price": "N/A", "brand": "N/A", "mass": "N/A"}

                detail_items = card.query_selector_all('dl > div')
                for item in detail_items:
                    dt = item.query_selector('dt')
                    dd = item.query_selector('dd')
                    if dt and dd:
                        label = dt.inner_text().strip().lower()
                        value = dd.inner_text().strip()

                        if 'dimensions' in label:
                            details["dimensions"] = value
                        elif 'color' in label:
                            details["color"] = value
                        elif 'price' in label:
                            details["price"] = value
                        elif 'brand' in label:
                            details["brand"] = value
                        elif 'mass' in label:
                            details["mass"] = f"{value} kg"

                updated_element = card.query_selector('span:has-text("Updated:")')
                updated = "N/A"
                if updated_element:
                    updated_text = updated_element.inner_text().strip()
                    if 'Updated:' in updated_text:
                        updated = updated_text.split('Updated:')[1].strip()

                product_data = {
                    "id": product_id,
                    "name": name,
                    "category": category,
                    "dimensions": details["dimensions"],
                    "color": details["color"],
                    "price": details["price"],
                    "brand": details["brand"],
                    "mass": details["mass"],
                    "updated": updated
                }

                all_products.append(product_data)

            except Exception as e:
                print(f"Error extracting product: {e}")
                continue

        print(f"Found {new_products} new products in this batch, total so far: {len(all_products)}")

        if len(all_products) >= 1830:
            print("Reached target product count!")
            break

        if new_products == 0:
            no_new_products_count += 1
            if no_new_products_count >= 5:
                print("No new products found in last 5 attempts, stopping.")
                break
        else:
            no_new_products_count = 0

        scroll_attempts += 1
        print(f"Scrolling attempt #{scroll_attempts}")

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)

        can_scroll_more = page.evaluate("""
            () => window.innerHeight + window.scrollY < document.body.scrollHeight - 100
        """)
        if not can_scroll_more:
            print("Reached bottom of the page.")
            break

    print(f"Scraping complete. Total products extracted: {len(all_products)}")
    return all_products

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = None

        storage_state = load_session()
        if storage_state:
            print("Loading existing session...")
            context = browser.new_context(storage_state=storage_state)
        else:
            print("No session found, starting new context")
            context = browser.new_context()

        page = context.new_page()
        page.set_default_timeout(30000)
        page.set_viewport_size({"width": 1280, "height": 800})

        try:
            page.goto(BASE_URL)

            if page.url == LOGIN_URL or page.query_selector('input[type="email"]'):
                storage_state = authenticate(page)
                save_session(storage_state)

            if page.url == INSTRUCTIONS_URL:
                if not navigate_to_challenge(page):
                    print("Failed to navigate to challenge page")
                    return

            if page.url != CHALLENGE_URL:
                page.goto(CHALLENGE_URL)
                page.wait_for_selector("#inventory-card", timeout=60000)

            navigate_flippable_cards(page)

            products = scroll_and_extract_products(page)

            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)

            print(f"Data successfully exported to {OUTPUT_FILE}")
            print(f"Total products extracted: {len(products)}")

        except PlaywrightTimeoutError as e:
            print(f"Timeout error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
