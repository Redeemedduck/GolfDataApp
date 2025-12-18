"""Debug script to inspect the actual Uneekor page structure"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

url = "https://my.uneekor.com/power-u-report?id=40945&key=pc0VcwgCBkYKZpHf&distance=yard&speed=mph"

options = webdriver.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    print("Loading URL...")
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # Wait for page to load
    time.sleep(5)

    print("\n=== PAGE TITLE ===")
    print(driver.title)

    # Try to find the table
    print("\n=== LOOKING FOR TABLE ELEMENTS ===")

    # Try different selectors
    selectors_to_try = [
        ("tbody", By.TAG_NAME),
        ("table", By.TAG_NAME),
        ("tr", By.TAG_NAME),
        ("[role='table']", By.CSS_SELECTOR),
        (".table", By.CSS_SELECTOR),
        ("div[role='row']", By.CSS_SELECTOR),
    ]

    for selector, by_type in selectors_to_try:
        try:
            elements = driver.find_elements(by_type, selector)
            print(f"  {selector}: Found {len(elements)} elements")
            if len(elements) > 0 and len(elements) < 5:
                for i, elem in enumerate(elements[:3]):
                    print(f"    Element {i}: tag={elem.tag_name}, text={elem.text[:100]}")
        except Exception as e:
            print(f"  {selector}: Error - {e}")

    # Try to get all table rows
    print("\n=== TRYING tbody tr ===")
    try:
        table_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        print(f"Found {len(table_rows)} rows")
        if len(table_rows) > 0:
            print("\n=== FIRST ROW ANALYSIS ===")
            first_row = table_rows[0]
            print(f"Row text: {first_row.text}")
            print(f"Row HTML: {first_row.get_attribute('outerHTML')[:500]}")

            cols = first_row.find_elements(By.TAG_NAME, "td")
            print(f"Number of columns: {len(cols)}")
            for i, col in enumerate(cols[:10]):
                print(f"  Col {i}: {col.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Save page source for inspection
    print("\n=== SAVING PAGE SOURCE ===")
    with open("debug_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved to debug_page_source.html")

    # Keep browser open for manual inspection
    print("\n=== Browser will stay open for 30 seconds for manual inspection ===")
    time.sleep(30)

except Exception as e:
    print(f"Critical Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("\nBrowser closed.")
