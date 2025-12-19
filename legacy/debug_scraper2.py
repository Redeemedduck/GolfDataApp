"""Debug script v2 - Look for shot data specifically"""
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

    # Wait longer for dynamic content
    time.sleep(8)

    print("\n=== LOOKING FOR TABLES ===")
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"Found {len(tables)} tables")

    for i, table in enumerate(tables):
        print(f"\n=== TABLE {i} ===")
        print(f"Table classes: {table.get_attribute('class')}")
        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"Rows in table: {len(rows)}")

        if len(rows) > 0:
            print(f"\nFirst 3 rows:")
            for j, row in enumerate(rows[:3]):
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 0:
                    print(f"  Row {j}: {len(cols)} cols - {[col.text for col in cols[:10]]}")

    # Also check if there's a specific ID or class we should be looking for
    print("\n=== LOOKING FOR SHOT DATA BY TEXT ===")
    # Look for elements containing club names
    all_text = driver.find_element(By.TAG_NAME, "body").text
    if "candlestone" in all_text.lower() or "iron 7" in all_text.lower():
        print("Found club names in page text!")
        print("Searching for elements with club names...")

        # Try to find elements containing these club names
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'candlestone') or contains(text(), 'Iron 7')]")
        print(f"Found {len(elements)} elements with club names")

        for elem in elements[:3]:
            print(f"  Element: {elem.tag_name}, text: {elem.text}, parent: {elem.find_element(By.XPATH, '..').tag_name}")

    print("\n=== Keeping browser open for 60 seconds ===")
    time.sleep(60)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
