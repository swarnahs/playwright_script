import asyncio
import json
import os
from playwright.async_api import async_playwright

SESSION_FILE = "session.json"
OUTPUT_FILE = "products.json"

# 🔹 Your credentials (use env vars for security)
USERNAME = os.getenv("SCRAPER_USER", "your_username")
PASSWORD = os.getenv("SCRAPER_PASS", "your_password")
LOGIN_URL = os.getenv("TARGET_URL", "https://your-app.com/login")

async def save_session(context):
    """Save authentication state to a file"""
    await context.storage_state(path=SESSION_FILE)

async def load_session(browser):
    """Load session if available, else return None"""
    if os.path.exists(SESSION_FILE):
        context = await browser.new_context(storage_state=SESSION_FILE)
        return context
    return None

async def login_and_save(browser):
    """Perform login and save session"""
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(LOGIN_URL)

    # Fill login form
    await page.fill("input[name='username']", USERNAME)
    await page.fill("input[name='password']", PASSWORD)
    await page.click("button[type='submit']")

    # Wait for navigation after login
    await page.wait_for_load_state("networkidle")

    # Save session
    await save_session(context)
    return context

async def scrape_products(page):
    """Scrape product table with pagination support"""
    products = []

    while True:
        # Wait for table
        await page.wait_for_selector("table")

        rows = await page.query_selector_all("table tbody tr")
        for row in rows:
            cells = await row.query_selector_all("td")
            values = [await c.inner_text() for c in cells]
            products.append(values)

        # Check if next page button exists and is enabled
        next_button = await page.query_selector("button.next, a.next")
        if next_button:
            disabled = await next_button.get_attribute("disabled")
            if disabled:
                break
            await next_button.click()
            await page.wait_for_load_state("networkidle")
        else:
            break

    return products

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # 🔹 Try to load existing session
        context = await load_session(browser)
        if not context:
            print("⚡ No session found, logging in...")
            context = await login_and_save(browser)
        else:
            print("✅ Using saved session")

        page = await context.new_page()

        # 🔹 Navigate through card flips
        await page.goto("https://your-app.com/dashboard")
        await page.click("text=Dashboard")
        await page.click("text=Inventory")
        await page.click("text=Catalog")
        await page.click("text=View Complete Data")

        # 🔹 Scrape products
        products = await scrape_products(page)

        # 🔹 Export JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

        print(f"📂 Exported {len(products)} products to {OUTPUT_FILE}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
