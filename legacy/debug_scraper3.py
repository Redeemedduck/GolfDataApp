"""Debug script v3 - Try different text extraction methods"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

url = "https://my.uneekor.com/power-u-report?id=40945&key=pc0VcwgCBkYKZpHf&distance=yard&speed=mph"

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get(url)
    print("Waiting for page to load...")
    time.sleep(10)  # Wait longer for React to render

    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\nFound {len(tables)} tables")

    # Focus on table 1 which has 8 columns
    if len(tables) > 1:
        table = tables[1]
        print(f"\n=== ANALYZING TABLE 1 (Shot Data Table) ===")

        rows = table.find_elements(By.TAG_NAME, "tr")
        print(f"Total rows: {len(rows)}")

        for i, row in enumerate(rows[:5]):
            print(f"\n--- Row {i} ---")
            print(f"Row .text: '{row.text}'")
            print(f"Row .get_attribute('textContent'): '{row.get_attribute('textContent')}'")
            print(f"Row innerHTML (first 200 chars): {row.get_attribute('innerHTML')[:200]}")

            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 0:
                cols = row.find_elements(By.TAG_NAME, "th")
                print(f"  This is a header row with {len(cols)} columns")

            for j, col in enumerate(cols[:8]):
                text = col.text
                textContent = col.get_attribute('textContent')
                innerHTML = col.get_attribute('innerHTML')
                print(f"  Col {j}: .text='{text}', .textContent='{textContent}', innerHTML={innerHTML[:50] if innerHTML else 'None'}")

    print("\n=== Browser staying open for inspection ===")
    time.sleep(60)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
