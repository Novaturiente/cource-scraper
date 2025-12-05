import csv
import os
import re
import time
import threading
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt

# Global list for logs to be accessed by TUI
logs = []
log_lock = threading.Lock()

def log(msg):
    with log_lock:
        logs.append(msg)
        # Keep buffer reasonable
        if len(logs) > 100:
            logs.pop(0)

def scrape_logic(country_name, layout, progress, page_task, status_table):
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

        # 3. Now navigate to SearchProgram page
        driver.get("https://www.coursefinder.ai/SearchProgram")
        time.sleep(5)

        # Open advanced search and set the country
        advanced_search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[3]/a")
            )
        )
        advanced_search_button.click()
        log("✓ Advanced Search button clicked")
        time.sleep(2)

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
        
        dropdown_button.click()
        time.sleep(0.5)

        # ITERATE THROUGH ALL YEARS
        for year_index, selected_year in enumerate(year_options):
            if selected_year != "2026":
                log(f"⏭️  Skipping year {selected_year} (only processing 2026)")
                continue

            log(f"PROCESSING YEAR: {selected_year}")
            
            # Update Status Table
            # We need to recreate the table to update it in Rich
            # But since we are in a thread, we can't easily modify the layout object directly if it's not thread-safe?
            # Actually, we can just update a shared state or the table object if we are careful.
            # Better: The main loop regenerates the table. We just update variables.
            # Let's use a shared dict for status.
            status_table["Year"] = selected_year
            status_table["Country"] = country_name

            driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            time.sleep(1)

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

            checkbox_section_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div"
            checkboxes = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, f"{checkbox_section_xpath}//input[@type='checkbox']")
                )
            )

            button_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[1]/div/div[1]/div[2]/button[2]"
            label_base_xpath = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div/ul/li"
            results_section_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/div[2]/div"

            # CSV Setup
            all_articles_data = []
            csv_filename = f"{country_name.replace(' ', '_')}-cources-{selected_year}.csv"
            csv_path = os.path.join(os.getcwd(), csv_filename)
            fieldnames = ["Year", "Program Level", "Course", "Course URL", "University", "Country", "Duration", "Open Semesters", "Closed Semesters", "Speciality", "Rankings", "Yearly Tuition Fee", "Application Fee", "Page Number"]
            header_written = False
            
            log(f"📄 CSV file: {csv_filename}")

            processed_checkboxes = set()
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    if rows:
                        seen_levels = []
                        for row in rows:
                            level = row.get("Program Level")
                            if level and level not in seen_levels:
                                seen_levels.append(level)
                        if seen_levels:
                            last_level = seen_levels[-1]
                            completed_levels = seen_levels[:-1]
                            processed_checkboxes = set(completed_levels)
                            valid_rows = [r for r in rows if r.get("Program Level") in processed_checkboxes]
                            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(valid_rows)
                            header_written = True
                            log(f"Resuming from {last_level}...")
                except Exception as e:
                    log(f"Error reading existing CSV: {e}")

            if checkboxes:
                for i, checkbox in enumerate(checkboxes):
                    checkbox_value = checkbox.get_attribute("value")
                    
                    checkbox_name = "Unknown"
                    try:
                        label_xpath = f"{label_base_xpath}[{i + 1}]/div/label"
                        label_element = driver.find_element(By.XPATH, label_xpath)
                        checkbox_name = label_element.text.strip()
                    except:
                        pass
                    
                    status_table["Current Checkbox"] = checkbox_name
                    
                    if checkbox_name in processed_checkboxes:
                        log(f"Skipping {checkbox_name} (already done)")
                        continue

                    if not checkbox.is_selected():
                        driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(1)
                    
                    old_results_text = ""
                    try:
                        old_element = driver.find_element(By.XPATH, results_section_xpath)
                        old_results_text = old_element.text.strip()
                    except:
                        pass

                    button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, button_xpath)))
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", button)
                    log(f"Searching {checkbox_name}...")

                    try:
                        def results_have_changed(driver):
                            try:
                                new_element = driver.find_element(By.XPATH, results_section_xpath)
                                new_text = new_element.text.strip()
                                return new_text != old_results_text and new_text != ""
                            except:
                                return False
                        WebDriverWait(driver, 30).until(results_have_changed)
                        time.sleep(2)
                    except TimeoutException:
                        log("Timeout waiting for data update.")

                    try:
                        results_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, results_section_xpath)))
                        results_text = results_element.text.strip()
                        
                        pages_match = re.search(r"Page\s+\d+\s+of\s+(\d+)", results_text, re.IGNORECASE)
                        num_pages = pages_match.group(1) if pages_match else "1"
                        total_pages = int(num_pages)
                        
                        log(f"Found {total_pages} pages for {checkbox_name}")
                        
                        # Reset progress bar for this checkbox
                        progress.update(page_task, total=total_pages, completed=0, description=f"Pages ({checkbox_name})")

                        articles_section_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]"
                        article_xpath = f"{articles_section_xpath}/article"
                        next_page_button_xpath = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/nav/ul/li[3]/a"

                        current_page = 1
                        while current_page <= total_pages:
                            # log(f"Processing Page {current_page}/{total_pages}")
                            progress.update(page_task, completed=current_page)
                            time.sleep(2)

                            try:
                                articles = driver.find_elements(By.XPATH, article_xpath)
                                for article in articles:
                                    try:
                                        article_data = {}
                                        article_data["Year"] = selected_year
                                        article_data["Program Level"] = checkbox_name
                                        
                                        # Title
                                        try:
                                            title_element = article.find_element(By.CSS_SELECTOR, "h3 a")
                                            article_data["Course"] = title_element.text.strip()
                                            article_data["Course URL"] = title_element.get_attribute("href")
                                        except:
                                            article_data["Course"] = "Not found"
                                            article_data["Course URL"] = "Not found"

                                        # University
                                        try:
                                            uni_panel = article.find_element(By.CSS_SELECTOR, "div.uni_countryPanel.clearfix")
                                            university_div = uni_panel.find_element(By.CSS_SELECTOR, "div[class*='universityProgram']")
                                            try:
                                                university_name = university_div.find_element(By.CSS_SELECTOR, "div.con_text").text.strip()
                                            except:
                                                university_name = university_div.text.strip()
                                            article_data["University"] = university_name if university_name else "Not found"
                                        except:
                                            article_data["University"] = "Not found"

                                        # Speciality
                                        article_data["Speciality"] = "Not found"
                                        try:
                                            highlight_badge_wrap = article.find_element(By.CSS_SELECTOR, "div.highlight-badge-wrap")
                                            badge_spans = highlight_badge_wrap.find_elements(By.XPATH, "./span")
                                            badges = []
                                            for badge_span in badge_spans:
                                                full_text = badge_span.text.strip()
                                                try:
                                                    symbol_span = badge_span.find_element(By.XPATH, "./span")
                                                    symbol_text = symbol_span.text.strip()
                                                    badge_text = full_text.replace(symbol_text, "").strip()
                                                except:
                                                    badge_text = full_text
                                                if badge_text:
                                                    badges.append(badge_text)
                                            if badges:
                                                article_data["Speciality"] = ", ".join(badges)
                                        except:
                                            pass

                                        # Rankings
                                        article_data["Rankings"] = "Not found"
                                        try:
                                            ranking_section = article.find_element(By.CSS_SELECTOR, "div.ranking-details")
                                            rank_divs = ranking_section.find_elements(By.CSS_SELECTOR, "div.rankborder.sp-rankborder")
                                            rankings = []
                                            for rank_div in rank_divs:
                                                try:
                                                    rank_text = rank_div.find_element(By.CSS_SELECTOR, "span.rank").text.strip()
                                                    ranking_text = rank_div.find_element(By.CSS_SELECTOR, "span.ranking").text.strip()
                                                    if rank_text and ranking_text:
                                                        rankings.append(f"{rank_text} {ranking_text}")
                                                except:
                                                    pass
                                            if rankings:
                                                article_data["Rankings"] = ", ".join(rankings)
                                        except:
                                            pass

                                        # Country
                                        try:
                                            country_elements = article.find_elements(By.XPATH, f".//*[contains(text(), '{country_name}')]")
                                            article_data["Country"] = country_elements[0].text.strip() if country_elements else "Not found"
                                        except:
                                            article_data["Country"] = "Not found"

                                        # Text parsing
                                        article_text = article.text.strip()
                                        lines = article_text.split("\n")

                                        article_data["Duration"] = "Not found"
                                        for j, line in enumerate(lines):
                                            if "Duration:" in line and j + 1 < len(lines):
                                                article_data["Duration"] = lines[j + 1]
                                                break
                                        
                                        # Intakes
                                        article_data["Open Semesters"] = "Not found"
                                        article_data["Closed Semesters"] = "Not found"
                                        try:
                                            intake_div = article.find_element(By.CSS_SELECTOR, "div.divintake")
                                            try:
                                                open_intake_div = intake_div.find_element(By.CSS_SELECTOR, "div.openIntakeDiv")
                                                open_spans = open_intake_div.find_elements(By.TAG_NAME, "span")
                                                open_semesters = [span.text.strip() for span in open_spans[1:] if span.text.strip()]
                                                if open_semesters:
                                                    article_data["Open Semesters"] = ", ".join(open_semesters)
                                            except:
                                                pass
                                            try:
                                                closed_intake_div = intake_div.find_element(By.CSS_SELECTOR, "div.closedIntakeDiv")
                                                closed_spans = closed_intake_div.find_elements(By.TAG_NAME, "span")
                                                closed_semesters = [span.text.strip() for span in closed_spans[1:] if span.text.strip()]
                                                if closed_semesters:
                                                    article_data["Closed Semesters"] = ", ".join(closed_semesters)
                                            except:
                                                pass
                                        except:
                                            pass

                                        # Fees
                                        article_data["Yearly Tuition Fee"] = "Not found"
                                        for j, line in enumerate(lines):
                                            if "Yearly Tuition Fee:" in line:
                                                fee_text = line.replace("Yearly Tuition Fee:", "").strip()
                                                if fee_text:
                                                    article_data["Yearly Tuition Fee"] = fee_text
                                                elif j + 1 < len(lines):
                                                    article_data["Yearly Tuition Fee"] = lines[j + 1].split("Application Fee:")[0].strip()
                                                break
                                        
                                        article_data["Application Fee"] = "Not found"
                                        for line in lines:
                                            if "Application Fee:" in line:
                                                fee_text = line.replace("Application Fee:", "").strip()
                                                article_data["Application Fee"] = fee_text if fee_text else "Not found"
                                                break
                                        
                                        article_data["Page Number"] = current_page
                                        all_articles_data.append(article_data)

                                    except:
                                        pass
                                
                                # Incremental Write
                                page_articles = [a for a in all_articles_data if a.get("Program Level") == checkbox_name and a.get("Page Number") == current_page]
                                if page_articles:
                                    mode = "w" if not header_written else "a"
                                    with open(csv_path, mode, newline="", encoding="utf-8") as csvfile:
                                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                        if not header_written:
                                            writer.writeheader()
                                            header_written = True
                                        writer.writerows(page_articles)
                                    # log(f"Saved {len(page_articles)} articles from page {current_page}")

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
                        log(f"Error extracting results info: {e}")

                    if checkbox.is_selected():
                        driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(1)

    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        driver.quit()
        log("Browser closed.")
        status_table["Status"] = "Finished"

def main():
    console = Console()
    country_name = Prompt.ask("[bold green]Enter Country Name[/bold green]", default="United Kingdom")
    
    # TUI Setup
    status_table_data = {
        "Country": country_name,
        "Year": "Initializing...",
        "Current Checkbox": "Waiting...",
        "Status": "Running"
    }

    def generate_status_table():
        table = Table(title="Scraper Status", expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in status_table_data.items():
            table.add_row(k, v)
        return table

    layout = Layout()
    layout.split(
        Layout(name="header", size=12),
        Layout(name="body", ratio=1)
    )

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}")
    )
    page_task = progress.add_task("Pages", total=100) # Initial dummy total

    # Start scraping thread
    t = threading.Thread(target=scrape_logic, args=(country_name, layout, progress, page_task, status_table_data))
    t.start()

    with Live(layout, refresh_per_second=4, screen=True, console=console) as live:
        while t.is_alive():
            # Update Header
            layout["header"].update(
                Panel(
                    Group(
                        generate_status_table(),
                        progress
                    ),
                    title="Scraper Dashboard",
                    border_style="blue"
                )
            )
            
            # Update Body (Logs)
            # Dynamic Scrolling Logic
            console_height = live.console.height
            header_height = 12
            available_height = max(5, console_height - header_height - 2)
            
            with log_lock:
                visible_logs = logs[-available_height:]
                log_content = "\n".join(visible_logs)

            layout["body"].update(
                Panel(
                    log_content,
                    title="Activity Log",
                    border_style="green"
                )
            )
            
            time.sleep(0.2)
    
    console.print("Scraping completed.")

if __name__ == "__main__":
    main()
