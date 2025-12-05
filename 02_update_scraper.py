import csv
import os
import re
import threading
import time
from datetime import datetime

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Global list for logs to be accessed by TUI
logs = []
log_lock = threading.Lock()


def log(msg):
    with log_lock:
        logs.append(msg)
        if len(logs) > 100:
            logs.pop(0)


# --- CONSTANTS ---
PROGRAM_LEVELS = [
    "High School (11th - 12th)",
    "UG Diploma/ Certificate/ Associate Degree",
    "UG",
    "PG Diploma/ Certificate",
    "PG",
    "UG + PG (Accelerated Degree)",
    "PhD",
    "Short-term/Summer Programs",
    "Pathway Programs (UG)",
    "Pathway Programs (PG)",
    "Semester Study Abroad",
    "Twinning Programs (UG)",
    "Twinning Programs (PG)",
    "English Language Program",
    "Online Programs / Distance Learning",
]

STUDY_AREAS = [
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
    "Veterinary",
]

REQUIREMENTS = [
    "PTE",
    "TOEFL iBT",
    "IELTS",
    "DET",
    "SAT",
    "ACT",
    "GRE",
    "GMAT",
    "Without English Proficiency",
    "Without GRE",
    "Without GMAT",
    "Without Maths",
    "Application Fee Waiver (upto 100%)",
    "Scholarship Available",
    "With 15 Years of Education",
]

# --- SELECTORS ---
CHECKBOX_SECTION_XPATH = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div"
PROGRAM_LEVEL_CONTAINER_XPATH = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[1]/div/div/ul"
STUDY_AREA_BUTTON_SELECTOR = (
    "#h2margin5px > div > div:nth-child(2) > div:nth-child(3) > div > button"
)
STUDY_AREA_SEARCH_INPUT_XPATH = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[3]/div/div/div[1]/input"
SEARCH_BUTTON_XPATH = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[1]/div/div[1]/div[2]/button[2]"
RESULTS_SECTION_XPATH = (
    "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/div[2]/div"
)
REQUIREMENTS_CONTAINER_XPATH = "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[3]/div/div/ul"
ARTICLES_SECTION_XPATH = "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]"
ARTICLE_XPATH = f"{ARTICLES_SECTION_XPATH}/article"
NEXT_PAGE_BUTTON_XPATH = (
    "/html/body/div[2]/section/div/div[2]/div[4]/div[2]/div[2]/nav/ul/li[3]/a"
)


def get_driver():
    options = Options()
    profile_dir = os.path.join(os.environ.get("TEMP_DIR", "."), "chrome_profile")
    options.add_argument(f"user-data-dir={profile_dir}")
    log_path = os.path.join(os.environ.get("TEMP_DIR", "."), "chromedriver.log")
    service = ChromeService(
        ChromeDriverManager().install(),
        service_args=["--verbose", f"--log-path={log_path}"],
    )
    return webdriver.Chrome(service=service, options=options)


def login_if_needed(driver):
    driver.get("https://www.coursefinder.ai/Dashboard")
    time.sleep(3)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'Logout')]"))
        )
        log("Already logged in.")
    except:
        log("Not logged in. Performing login.")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "email"))
            ).send_keys("canadaeec@gmail.com")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "password"))
            ).send_keys("EEC@baroda123")
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "btn-login"))
            ).click()
            log("Login submitted successfully.")
            time.sleep(5)
        except Exception as e:
            log(f"Login failed: {e}")


def setup_search_page(driver, country_name):
    driver.get("https://www.coursefinder.ai/SearchProgram")
    time.sleep(5)

    # Advanced Search
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[3]/a",
            )
        )
    ).click()
    time.sleep(2)

    # Country
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[1]/div",
            )
        )
    ).click()
    country_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[2]/section/div/div[2]/div[1]/div/form/div[1]/div/div/div[4]/div/div[2]/div/div/div[2]/div/div[1]/div[1]/div/div[2]/div/div[1]/input",
            )
        )
    )
    country_input.send_keys(country_name)
    time.sleep(1)
    country_input.send_keys(Keys.ENTER)
    log(f"✓ Country set to: {country_name}")

    # Year (2026)
    dropdown_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-id="Year"]'))
    )
    dropdown_button.click()
    time.sleep(1)
    year_options = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.dropdown-menu ul.dropdown-menu.inner.show li")
        )
    )
    for option in year_options:
        if option.text.strip() == "2026":
            option.click()
            log("✓ Year set to: 2026")
            break
    time.sleep(1)


def wait_for_overlay(driver):
    try:
        WebDriverWait(driver, 2).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "sweet-overlay"))
        )
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "sweet-overlay"))
        )
        time.sleep(1)
    except:
        time.sleep(2)


def click_search(driver):
    search_btn = driver.find_element(By.XPATH, SEARCH_BUTTON_XPATH)
    driver.execute_script("arguments[0].click();", search_btn)
    wait_for_overlay(driver)


def select_program_level(driver, level_name):
    try:
        checkbox_xpath = f"{PROGRAM_LEVEL_CONTAINER_XPATH}//li//label[normalize-space()='{level_name}']//input[@type='checkbox']"
        checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, checkbox_xpath))
        )
        if not checkbox.is_selected():
            driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(1)
        return checkbox
    except Exception as e:
        log(f"Error selecting program level {level_name}: {e}")
        return None


def deselect_program_level(driver, checkbox):
    if checkbox and checkbox.is_selected():
        driver.execute_script("arguments[0].click();", checkbox)
        time.sleep(1)


def update_tags(driver, level_name, csv_path, update_mode, status_table):
    log(f"--- Updating Tags for {level_name} (Mode: {update_mode}) ---")

    # Load CSV into memory
    courses_db = {}  # Key: (Course, University), Value: Row Dict
    fieldnames = []

    if not os.path.exists(csv_path):
        log("CSV not found, skipping.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            key = (row.get("Course"), row.get("University"))
            courses_db[key] = row

    # --- SPECIAL REQUIREMENTS ---
    if update_mode in ["Special Requirements", "Both"]:
        log(f"Starting Special Requirements Loop for {level_name}")
        status_table["Current Study Area"] = "None (Req Loop)"

        for req_name in REQUIREMENTS:
            status_table["Current Requirement"] = req_name

            # Select Requirement
            req_checkbox_xpath = f"{REQUIREMENTS_CONTAINER_XPATH}//li//label[normalize-space()='{req_name}']//input[@type='checkbox']"
            try:
                req_checkbox = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, req_checkbox_xpath))
                )
                if not req_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", req_checkbox)
                    time.sleep(0.5)

                # Search
                click_search(driver)

                # Check results
                try:
                    res_el = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, RESULTS_SECTION_XPATH))
                    )
                    if "No Record Found" in res_el.text:
                        # Deselect and continue
                        if req_checkbox.is_selected():
                            driver.execute_script("arguments[0].click();", req_checkbox)
                        continue

                    # Iterate pages (lightweight scraping)
                    pages_match = re.search(
                        r"Page\s+\d+\s+of\s+(\d+)", res_el.text, re.IGNORECASE
                    )
                    total_pages = int(pages_match.group(1)) if pages_match else 1

                    curr = 1
                    while curr <= total_pages:
                        articles = driver.find_elements(By.XPATH, ARTICLE_XPATH)
                        for article in articles:
                            try:
                                c_name = article.find_element(
                                    By.CSS_SELECTOR, "h3 a"
                                ).text.strip()
                                try:
                                    u_name = article.find_element(
                                        By.CSS_SELECTOR,
                                        "div[class*='universityProgram'] div.con_text",
                                    ).text.strip()
                                except:
                                    u_name = article.find_element(
                                        By.CSS_SELECTOR, "div[class*='universityProgram']"
                                    ).text.strip()

                                key = (c_name, u_name)
                                if key in courses_db:
                                    # Update Tags
                                    row = courses_db[key]
                                    current_req = row.get("Special Requirements", "")
                                    if req_name not in current_req:
                                        row["Special Requirements"] = (
                                            f"{current_req}, {req_name}"
                                            if current_req
                                            else req_name
                                        )
                            except:
                                pass

                        # Next page
                        if curr < total_pages:
                            try:
                                nxt = driver.find_element(By.XPATH, NEXT_PAGE_BUTTON_XPATH)
                                driver.execute_script(
                                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                    nxt,
                                )
                                driver.execute_script("arguments[0].click();", nxt)
                                time.sleep(2)
                            except:
                                break
                        curr += 1

                except:
                    pass

                # Deselect Requirement
                if req_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", req_checkbox)
                    time.sleep(0.5)

                # SAVE PROGRESS
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(courses_db.values())
                log(f"Saved tags for Requirement: {req_name}")

            except Exception as e:
                log(f"Error in Requirement loop for {req_name}: {e}")

    # --- STUDY AREAS ---
    if update_mode in ["Area of Study", "Both"]:
        log(f"Starting Study Areas Loop for {level_name}")
        status_table["Current Requirement"] = "None (SA Loop)"

        previous_sa = None

        for sa_name in STUDY_AREAS:
            status_table["Current Study Area"] = sa_name

            try:
                # Open Dropdown
                btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, STUDY_AREA_BUTTON_SELECTOR)
                    )
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    btn,
                )
                time.sleep(1)
                btn.click()
                time.sleep(1)

                inp = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, STUDY_AREA_SEARCH_INPUT_XPATH)
                    )
                )

                # Deselect Previous
                if previous_sa:
                    inp.clear()
                    time.sleep(1)
                    inp.send_keys(previous_sa)
                    time.sleep(1)
                    inp.send_keys(Keys.ENTER)
                    time.sleep(1)
                    inp.clear()
                    time.sleep(1)

                # Select Current
                inp.send_keys(sa_name)
                time.sleep(1)
                inp.send_keys(Keys.ENTER)
                time.sleep(1)

                # Close dropdown
                search_btn = driver.find_element(By.XPATH, SEARCH_BUTTON_XPATH)
                driver.execute_script("arguments[0].click();", search_btn)
                time.sleep(1)

                # Search
                click_search(driver)

                # Check results
                try:
                    res_el = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, RESULTS_SECTION_XPATH))
                    )
                    if "No Record Found" in res_el.text:
                        pass
                    else:
                        # Iterate pages
                        pages_match = re.search(
                            r"Page\s+\d+\s+of\s+(\d+)", res_el.text, re.IGNORECASE
                        )
                        total_pages = int(pages_match.group(1)) if pages_match else 1

                        curr = 1
                        while curr <= total_pages:
                            articles = driver.find_elements(By.XPATH, ARTICLE_XPATH)
                            for article in articles:
                                try:
                                    c_name = article.find_element(
                                        By.CSS_SELECTOR, "h3 a"
                                    ).text.strip()
                                    try:
                                        u_name = article.find_element(
                                            By.CSS_SELECTOR,
                                            "div[class*='universityProgram'] div.con_text",
                                        ).text.strip()
                                    except:
                                        u_name = article.find_element(
                                            By.CSS_SELECTOR,
                                            "div[class*='universityProgram']",
                                        ).text.strip()

                                    key = (c_name, u_name)
                                    if key in courses_db:
                                        # Update Tags
                                        row = courses_db[key]
                                        current_sa = row.get("Area of Study", "")
                                        if sa_name not in current_sa:
                                            row["Area of Study"] = (
                                                f"{current_sa}, {sa_name}"
                                                if current_sa
                                                else sa_name
                                            )
                                except:
                                    pass

                            # Next page
                            if curr < total_pages:
                                try:
                                    nxt = driver.find_element(
                                        By.XPATH, NEXT_PAGE_BUTTON_XPATH
                                    )
                                    driver.execute_script(
                                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                        nxt,
                                    )
                                    driver.execute_script("arguments[0].click();", nxt)
                                    time.sleep(2)
                                except:
                                    break
                            curr += 1

                except:
                    pass

                # Update previous
                previous_sa = sa_name

                # SAVE PROGRESS
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(courses_db.values())
                log(f"Saved tags for Study Area: {sa_name}")

            except Exception as e:
                log(f"Error processing Study Area {sa_name}: {e}")

        # Cleanup: Deselect last Study Area
        if previous_sa:
            try:
                btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, STUDY_AREA_BUTTON_SELECTOR)
                    )
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    btn,
                )
                time.sleep(1)
                btn.click()
                time.sleep(1)

                inp = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, STUDY_AREA_SEARCH_INPUT_XPATH)
                    )
                )
                inp.clear()
                time.sleep(1)
                inp.send_keys(previous_sa)
                time.sleep(1)
                inp.send_keys(Keys.ENTER)
                time.sleep(1)

                # Close dropdown
                search_btn = driver.find_element(By.XPATH, SEARCH_BUTTON_XPATH)
                driver.execute_script("arguments[0].click();", search_btn)
                time.sleep(1)

            except Exception as e:
                log(f"Error deselecting last Study Area: {e}")


def worker(csv_path, country_name, update_mode, layout, progress, status_table):
    driver = get_driver()
    try:
        login_if_needed(driver)
        setup_search_page(driver, country_name)

        # Identify Program Levels from CSV
        program_levels = set()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Program Level"):
                    program_levels.add(row["Program Level"])
        
        log(f"Found Program Levels in CSV: {program_levels}")

        for level in program_levels:
            status_table["Current Checkbox"] = level
            status_table["Current Study Area"] = "None"
            status_table["Current Requirement"] = "None"

            # Select Level
            cb = select_program_level(driver, level)
            if not cb:
                log(f"Could not select program level: {level}")
                continue

            # Update Tags
            update_tags(driver, level, csv_path, update_mode, status_table)

            # Deselect Level
            deselect_program_level(driver, cb)

    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        driver.quit()
        status_table["Status"] = "Finished"


def main():
    console = Console()
    
    # 1. Select CSV File
    csv_files = [f for f in os.listdir(".") if f.endswith(".csv")]
    if not csv_files:
        console.print("[bold red]No CSV files found in current directory![/bold red]")
        return

    console.print("\n[bold cyan]Available CSV Files:[/bold cyan]")
    for idx, f in enumerate(csv_files):
        console.print(f"[{idx + 1}] {f}")
    
    file_idx = Prompt.ask(
        "\n[bold green]Select CSV File (index)[/bold green]",
        choices=[str(i + 1) for i in range(len(csv_files))],
    )
    csv_path = os.path.abspath(csv_files[int(file_idx) - 1])
    console.print(f"Selected File: [bold yellow]{csv_path}[/bold yellow]")

    # 2. Country Name
    country_name = Prompt.ask(
        "[bold green]Enter Country Name[/bold green]", default="United Kingdom"
    )

    # 3. Update Mode
    console.print("\n[bold cyan]Update Mode:[/bold cyan]")
    console.print("[1] Area of Study")
    console.print("[2] Special Requirements")
    console.print("[3] Both")
    
    mode_choice = Prompt.ask(
        "\n[bold green]Select what to update[/bold green]",
        choices=["1", "2", "3"],
        default="3"
    )
    
    update_mode = "Both"
    if mode_choice == "1":
        update_mode = "Area of Study"
    elif mode_choice == "2":
        update_mode = "Special Requirements"

    # --- TUI Setup ---
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=10),
    )

    layout["header"].update(
        Panel(
            Text(f"Scraper Updater - {country_name} - {update_mode}", justify="center", style="bold white"),
            style="blue",
        )
    )

    status_table = {
        "Status": "Running",
        "Current Checkbox": "Initializing...",
        "Current Study Area": "None",
        "Current Requirement": "None",
    }

    def generate_status_table():
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        for k, v in status_table.items():
            table.add_row(k, str(v))
        return Panel(table, title="Status", border_style="green")

    def generate_log_panel():
        with log_lock:
            log_text = "\n".join(logs[-10:])
        return Panel(log_text, title="Logs", border_style="yellow")

    layout["body"].split_row(
        Layout(name="status"),
        Layout(name="logs"),
    )

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    layout["footer"].update(Panel(progress, title="Progress", border_style="blue"))

    # Start Worker
    t = threading.Thread(
        target=worker,
        args=(csv_path, country_name, update_mode, layout, progress, status_table),
        daemon=True,
    )
    t.start()

    with Live(layout, refresh_per_second=4, screen=True):
        while t.is_alive():
            layout["body"]["status"].update(generate_status_table())
            layout["body"]["logs"].update(generate_log_panel())
            time.sleep(0.25)

    console.print("[bold green]Update Completed![/bold green]")


if __name__ == "__main__":
    main()
