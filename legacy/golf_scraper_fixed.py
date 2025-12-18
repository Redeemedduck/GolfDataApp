import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import golf_db

MEDIA_DIR = "media"

def parse_float(text):
    try:
        clean_text = text.replace('R', '').replace('L', '').replace(',', '').strip()
        return float(clean_text)
    except:
        return 0.0

def run_scraper(url, progress_callback):
    try:
        if "id=" in url:
            session_id = re.search(r'id=(\d+)', url).group(1)
        else:
            session_id = "unknown_session"
    except:
        return "Error: Could not find Session ID in URL."

    session_media_path = f"{MEDIA_DIR}/{session_id}"
    os.makedirs(session_media_path, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        progress_callback("Opening Browser...")
        driver.get(url)

        # Wait longer for React to render
        progress_callback("Waiting for page to load...")
        time.sleep(10)

        # Get all session buttons from sidebar
        progress_callback("Finding sessions...")
        session_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='button']")

        sessions_to_process = []
        for btn in session_buttons:
            text_content = btn.get_attribute('textContent')
            if text_content and '(' in text_content and ')' in text_content:
                # Extract club name from format like "(16) candlestone"
                match = re.search(r'\((\d+)\)\s*(.+?)(?:\d{4}\.\d{2}\.\d{2}|$)', text_content)
                if match:
                    shot_count = match.group(1)
                    club_name = match.group(2).strip()
                    sessions_to_process.append((btn, club_name, shot_count))

        progress_callback(f"Found {len(sessions_to_process)} sessions")

        total_shots_imported = 0

        for session_btn, club_name, shot_count in sessions_to_process:
            progress_callback(f"Processing {club_name} ({shot_count} shots)...")

            # Click the session button
            driver.execute_script("arguments[0].click();", session_btn)
            time.sleep(3)  # Wait for table to update

            # Find the shot data table (second table)
            tables = driver.find_elements(By.TAG_NAME, "table")
            if len(tables) < 2:
                continue

            shot_table = tables[1]
            rows = shot_table.find_elements(By.TAG_NAME, "tr")

            # Skip header row (index 0), process data rows
            for row_index, row in enumerate(rows[1:], start=1):
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 3:
                        continue

                    # Extract data using textContent
                    col0_text = cols[0].get_attribute('textContent')  # "156.9166.44.4 R"
                    # Parse carry, total, side from first column
                    col0_parts = col0_text.split()
                    if len(col0_parts) < 2:
                        continue

                    # The first column has format like "156.9166.44.4 R"
                    # We need to parse: carry=156.9, total=166.4, side=4.4 R
                    # Let's find the divs inside
                    col0_divs = cols[0].find_elements(By.TAG_NAME, "div")
                    if len(col0_divs) >= 2:
                        carry_text = col0_divs[0].text or col0_divs[0].get_attribute('textContent')
                        total_text = col0_divs[1].text or col0_divs[1].get_attribute('textContent')

                        shot_data = {
                            'id': f"{session_id}_{club_name}_{row_index}",
                            'session': session_id,
                            'club': club_name,
                            'carry': parse_float(carry_text),
                            'total': parse_float(total_text),
                            'smash': 0.0,
                            'path': 0.0,
                            'face': 0.0,
                            'impact_img': None,
                            'swing_img': None
                        }

                        golf_db.save_shot(shot_data)
                        total_shots_imported += 1

                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue

        progress_callback(f"Completed! Imported {total_shots_imported} shots")
        return f"Success! Imported {total_shots_imported} shots."

    except Exception as e:
        return f"Critical Error: {str(e)}"
    finally:
        driver.quit()
