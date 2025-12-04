import csv
import os
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def scrape_logic(country_name):
    # Setup Chrome options for a persistent session
    options = Options()
    profile_dir = os.path.join(os.environ.get("TEMP_DIR", "."), "chrome_profile")
    options.add_argument(f"user-data-dir={profile_dir}")
    # options.add_argument("--headless") 

    log_path = os.path.join(os.environ.get("TEMP_DIR", "."), "chromedriver.log")
    service = ChromeService(
        ChromeDriverManager().install(),
        service_args=["--verbose", f"--log-path={log_path}"],
    )

    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 1. Navigate to the Dashboard (login page) first
        driver.get("https://www.coursefinder.ai/Dashboard")
        time.sleep(3)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'Logout')]"))
            )
            log("Already logged in.")
        except:
            log("Not logged in. Performing login.")
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                username_field.send_keys("canadaeec@gmail.com")

                password_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                password_field.send_keys("EEC@baroda123")

                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "btn-login"))
                )
                login_button.click()

                log("Login submitted successfully.")
                time.sleep(5)
            except Exception as e:
                log(f"Login failed: {e}")
                return

        # 3. Now navigate to SearchProgram page
        driver.get("https://www.coursefinder.ai/SearchProgram")
        time.sleep(5)

        # Open advanced search and set the country
        try:
            advanced_search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[3]/a")
                )
            )
            advanced_search_button.click()
            log("✓ Advanced Search button clicked")
            time.sleep(2)
        except Exception as e:
            log(f"Could not click Advanced Search: {e}")

        # Country Selection
        try:
            country_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[1]/div")
                )
            )
            country_dropdown.click()
            log("✓ Country dropdown clicked")

            country_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[1]/div/div[2]/div/div[1]/input")
                )
            )
            country_input.send_keys(country_name)
            time.sleep(1)
            country_input.send_keys(Keys.ENTER)
            log(f"✓ Entered '{country_name}' and pressed Enter")
        except Exception as e:
            log(f"Error selecting country: {e}")
            return

        # YEAR DROPDOWN
        dropdown_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-id="Year"]'))
        )
        dropdown_button.click()
        log("Year dropdown clicked to open.")
        time.sleep(2)

        year_option_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.dropdown-menu ul.dropdown-menu.inner.show li")
            )
        )

        year_options = []
        for option in year_option_elements:
            year_text = option.text.strip()
            if year_text:
                year_options.append(year_text)

        log(f"🗓️  Found {len(year_options)} year options: {', '.join(year_options)}")
        
        dropdown_button.click() # Close it for now
        time.sleep(0.5)

        # ITERATE THROUGH ALL YEARS
        for year_index, selected_year in enumerate(year_options):
            if selected_year != "2026":
                log(f"⏭️  Skipping year {selected_year} (only processing 2026)")
                continue

            log(f"PROCESSING YEAR: {selected_year}")

            driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            time.sleep(1)

            # Select Year
            dropdown_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-id="Year"]'))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", dropdown_button)
            time.sleep(0.5)
            dropdown_button.click()
            time.sleep(0.5)

            year_option_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.dropdown-menu ul.dropdown-menu.inner.show li")
                )
            )

            if year_index < len(year_option_elements):
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'nearest'});", year_option_elements[year_index])
                time.sleep(0.3)
                year_option_elements[year_index].click()
                log(f"✓ Selected year: {selected_year}")
                time.sleep(0.5)
            else:
                log(f"⚠ Could not select year at index {year_index}")
                continue

            # PROGRAM LEVEL CHECKBOXES
            checkbox_section_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div"
            try:
                checkboxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, f"{checkbox_section_xpath}//input[@type='checkbox']")
                    )
                )
            except:
                log("No program level checkboxes found.")
                continue

            # CSV Setup
            csv_filename = f"advanced-{country_name.replace(' ', '_')}-{selected_year}.csv"
            csv_path = os.path.join(os.getcwd(), csv_filename)
            fieldnames = ["Course", "Program Level", "Area of Study"]
            header_written = False
            
            if os.path.exists(csv_path):
                header_written = True # Assume header exists if file exists
            else:
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                header_written = True

            log(f"📄 CSV file: {csv_filename}")

            # ITERATE PROGRAM LEVELS
            for i in range(len(checkboxes)):
                # Re-find checkboxes to avoid stale element reference
                checkboxes = driver.find_elements(By.XPATH, f"{checkbox_section_xpath}//input[@type='checkbox']")
                if i >= len(checkboxes): break
                
                checkbox = checkboxes[i]
                checkbox_value = checkbox.get_attribute("value")
                
                checkbox_name = "Unknown"
                try:
                    label_base_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div/ul/li"
                    label_xpath = f"{label_base_xpath}[{i + 1}]/div/label"
                    label_element = driver.find_element(By.XPATH, label_xpath)
                    checkbox_name = label_element.text.strip()
                except:
                    pass
                
                log(f"--- Program Level: {checkbox_name} ---")

                if not checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", checkbox)
                    time.sleep(1)
                
                # --- STUDY AREA LOGIC START ---
                
                study_area_button_selector = "#h2margin5px > div > div:nth-child(2) > div:nth-child(3) > div > button"
                study_area_search_input_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[3]/div/div/div[1]/input"
                search_button_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[1]/div/div[1]/div[2]/button[2]"

                # Hardcoded list of Study Areas
                study_area_names = [
                    "Agriculture, Forestry and Fishery",
                    "Architecture and Building",
                    "Arts",
                    "Commerce, Business and Administration",
                    "Computer Science and Information Technology",
                    "Education",
                    "Engineering and Engineering Trades",
                    "Environmental Science/Protection",
                    "Health",
                    "Humanities",
                    "Journalism and Information",
                    "Law",
                    "Life Sciences",
                    "Manufacturing and Processing",
                    "Mathematics and Statistics",
                    "Personal Services",
                    "Physical Sciences, Sciences",
                    "Security Services",
                    "Social and Behavioural Science",
                    "Social Services",
                    "Transport Services",
                    "Veterinary"
                ]

                for sa_name in study_area_names:
                    try:
                        log(f"  > Processing: {sa_name}")
                        
                        # 1. SELECT & SCRAPE
                        # Open Dropdown
                        study_area_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, study_area_button_selector))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", study_area_button)
                        time.sleep(0.5)
                        study_area_button.click()
                        time.sleep(0.5)
                        
                        # Find Search Input
                        search_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, study_area_search_input_xpath))
                        )
                        
                        # Enter Name and Press Enter (Select)
                        search_input.clear()
                        time.sleep(0.2)
                        search_input.send_keys(sa_name)
                        time.sleep(0.5)
                        search_input.send_keys(Keys.ENTER)
                        time.sleep(0.5)
                        
                        # Click Search Button (Closes dropdown and searches)
                        search_btn = driver.find_element(By.XPATH, search_button_xpath)
                        driver.execute_script("arguments[0].click();", search_btn)
                        
                        # Wait for results
                        time.sleep(3)
                        
                        # Scrape
                        scrape_pages(driver, country_name, selected_year, checkbox_name, sa_name, csv_path, fieldnames)
                        
                        # 2. DESELECT (CLEANUP)
                        log(f"  > Deselecting: {sa_name}")
                        
                        # Open Dropdown
                        study_area_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, study_area_button_selector))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", study_area_button)
                        time.sleep(0.5)
                        study_area_button.click()
                        time.sleep(0.5)
                        
                        # Find Search Input
                        search_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, study_area_search_input_xpath))
                        )
                        
                        # Enter Name and Press Enter (Deselect)
                        search_input.clear()
                        time.sleep(0.2)
                        search_input.send_keys(sa_name)
                        time.sleep(0.5)
                        search_input.send_keys(Keys.ENTER)
                        time.sleep(0.5)
                        
                        # Clear input to be clean
                        search_input.clear()
                        time.sleep(0.2)
                        
                        # Click Search Button (Closes dropdown and updates - NO SCRAPE)
                        search_btn = driver.find_element(By.XPATH, search_button_xpath)
                        driver.execute_script("arguments[0].click();", search_btn)
                        
                        # Wait for results to load then wait 2 seconds
                        try:
                            results_section_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/div[2]/div"
                            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, results_section_xpath)))
                            time.sleep(2)
                        except:
                            pass

                    except Exception as e:
                        log(f"Error processing {sa_name}: {e}")
                        # Try to recover by closing dropdown if open
                        try:
                            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        except:
                            pass

                # --- STUDY AREA LOGIC END ---

                # Deselect Program Level
                if checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", checkbox)
                    time.sleep(1)

    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        driver.quit()
        log("Browser closed.")

def scrape_pages(driver, country_name, selected_year, program_level, study_area, csv_path, fieldnames):
    results_section_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/div[2]/div"
    try:
        # Wait for results to update/appear
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, results_section_xpath)))
            time.sleep(2) # Wait 2 seconds after results are loaded
        except:
            log("    No results found (timeout/empty).")
            return

        results_element = driver.find_element(By.XPATH, results_section_xpath)
        results_text = results_element.text.strip()
        
        # Check for "No courses found" or similar text if needed
        if "No courses found" in results_text or "No record found" in results_text:
             log("    No courses found.")
             return

        pages_match = re.search(r"Page\s+\d+\s+of\s+(\d+)", results_text, re.IGNORECASE)
        num_pages = pages_match.group(1) if pages_match else "1"
        total_pages = int(num_pages)
        
        log(f"    Found {total_pages} pages")

        articles_section_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]"
        article_xpath = f"{articles_section_xpath}/article"
        next_page_button_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/nav/ul/li[3]/a"

        current_page = 1
        while current_page <= total_pages:
            time.sleep(2)

            all_articles_data = []
            try:
                articles = driver.find_elements(By.XPATH, article_xpath)
                if not articles:
                    log(f"    ⚠ No articles found on page {current_page}")
                
                for article in articles:
                    try:
                        article_data = {}
                        article_data["Program Level"] = program_level
                        article_data["Area of Study"] = study_area
                        
                        # Title - Try multiple selectors
                        article_data["Course"] = "Not found"
                        
                        try:
                            title_element = article.find_element(By.CSS_SELECTOR, "h3 a")
                            article_data["Course"] = title_element.text.strip()
                        except:
                            try:
                                # Fallback: try finding h3 directly
                                title_element = article.find_element(By.TAG_NAME, "h3")
                                article_data["Course"] = title_element.text.strip()
                            except:
                                pass

                        all_articles_data.append(article_data)

                    except:
                        pass
                
                # Write to CSV
                if all_articles_data:
                    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writerows(all_articles_data)
                    log(f"    Saved {len(all_articles_data)} articles from page {current_page}")
                else:
                    log(f"    ⚠ No data extracted from page {current_page}")

            except Exception as e:
                log(f"Error extracting articles: {e}")

            if current_page < total_pages:
                try:
                    next_button = driver.find_element(By.XPATH, next_page_button_xpath)
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)
                except Exception as e:
                    log(f"Could not navigate to next page: {e}")
                    break
            
            current_page += 1

    except Exception as e:
        log(f"Error in scrape_pages: {e}")

def main():
    country_name = input("Enter Country Name [United Kingdom]: ") or "United Kingdom"
    scrape_logic(country_name)

if __name__ == "__main__":
    main()
