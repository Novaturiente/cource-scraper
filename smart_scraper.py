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


def scrape_base_courses(driver, level_name, csv_path, progress, page_task):
    log(f"--- Phase 1: Base Scraping for {level_name} ---")

    # Ensure no filters are active (Program Level is already selected by caller)
    click_search(driver)

    # Check pages
    try:
        results_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, RESULTS_SECTION_XPATH))
        )
        results_text = results_element.text.strip()
        if "No Record Found" in results_text:
            log(f"No courses found for {level_name}. Skipping.")
            return

        pages_match = re.search(r"Page\s+\d+\s+of\s+(\d+)", results_text, re.IGNORECASE)
        total_pages = int(pages_match.group(1)) if pages_match else 1
        log(f"Found {total_pages} pages of courses.")

        progress.update(
            page_task,
            total=total_pages,
            completed=0,
            description=f"Base Scraping ({level_name})",
        )

        fieldnames = [
            "Program Level",
            "Area of Study",
            "Special Requirements",
            "Course",
            "Course URL",
            "University",
            "Duration",
            "Open Semesters",
            "Closed Semesters",
            "Speciality",
            "Rankings",
            "Yearly Tuition Fee",
            "Application Fee",
        ]

        # Check if file exists to determine write mode
        file_exists = os.path.exists(csv_path)
        mode = "a" if file_exists else "w"

        current_page = 1
        while current_page <= total_pages:
            progress.update(page_task, completed=current_page)
            articles = driver.find_elements(By.XPATH, ARTICLE_XPATH)
            page_data = []

            for article in articles:
                try:
                    data = {}
                    data["Program Level"] = level_name
                    data["Area of Study"] = ""  # Empty for base
                    data["Special Requirements"] = ""  # Empty for base

                    # Basic extraction
                    try:
                        title_el = article.find_element(By.CSS_SELECTOR, "h3 a")
                        data["Course"] = title_el.text.strip()
                        data["Course URL"] = title_el.get_attribute("href")
                    except:
                        data["Course"] = "Not found"
                        data["Course URL"] = "Not found"

                    try:
                        uni_div = article.find_element(
                            By.CSS_SELECTOR, "div[class*='universityProgram']"
                        )
                        try:
                            data["University"] = uni_div.find_element(
                                By.CSS_SELECTOR, "div.con_text"
                            ).text.strip()
                        except:
                            data["University"] = uni_div.text.strip()
                    except:
                        data["University"] = "Not found"

                    # ... (Add other fields extraction similar to original scraper if needed, keeping it minimal for now or full?)
                    # User asked to "scrape all the cources", implying full details.
                    # I will copy the full extraction logic here for completeness.

                    # Speciality
                    data["Speciality"] = ""
                    try:
                        badges = [
                            s.text.strip()
                            for s in article.find_elements(
                                By.CSS_SELECTOR, "div.highlight-badge-wrap > span"
                            )
                        ]
                        data["Speciality"] = ", ".join([b for b in badges if b])
                    except:
                        pass

                    # Rankings
                    data["Rankings"] = ""
                    try:
                        ranks = [
                            r.text.strip().replace("\n", " ")
                            for r in article.find_elements(
                                By.CSS_SELECTOR, "div.rankborder.sp-rankborder"
                            )
                        ]
                        data["Rankings"] = ", ".join([r for r in ranks if r])
                    except:
                        pass

                    # Text parsing for Duration, Fees
                    text = article.text
                    lines = text.split("\n")

                    data["Duration"] = "Not found"
                    data["Yearly Tuition Fee"] = "Not found"
                    data["Application Fee"] = "Not found"

                    for i, line in enumerate(lines):
                        if "Duration:" in line and i + 1 < len(lines):
                            data["Duration"] = lines[i + 1]
                        if "Yearly Tuition Fee:" in line:
                            data["Yearly Tuition Fee"] = line.replace(
                                "Yearly Tuition Fee:", ""
                            ).strip()
                        if "Application Fee:" in line:
                            data["Application Fee"] = line.replace(
                                "Application Fee:", ""
                            ).strip()

                    # Intakes
                    data["Open Semesters"] = ""
                    data["Closed Semesters"] = ""
                    try:
                        open_s = [
                            s.text.strip()
                            for s in article.find_elements(
                                By.CSS_SELECTOR, "div.openIntakeDiv span"
                            )
                            if s.text.strip()
                        ]
                        data["Open Semesters"] = ", ".join(open_s[1:])  # Skip label
                    except:
                        pass
                    try:
                        closed_s = [
                            s.text.strip()
                            for s in article.find_elements(
                                By.CSS_SELECTOR, "div.closedIntakeDiv span"
                            )
                            if s.text.strip()
                        ]
                        data["Closed Semesters"] = ", ".join(closed_s[1:])
                    except:
                        pass

                    page_data.append(data)
                except Exception as e:
                    log(f"Error extracting article: {e}")

            # Write page data
            if page_data:
                with open(csv_path, mode, newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if mode == "w":
                        writer.writeheader()
                        mode = "a"  # Switch to append
                    writer.writerows(page_data)

            # Next page
            if current_page < total_pages:
                try:
                    next_btn = driver.find_element(By.XPATH, NEXT_PAGE_BUTTON_XPATH)
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        next_btn,
                    )
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                except:
                    break
            current_page += 1

    except Exception as e:
        log(f"Error in base scraping: {e}")


def tag_courses(driver, level_name, csv_path, status_table):
    log(f"--- Phase 2: Tagging for {level_name} ---")

    # Load CSV into memory
    courses_db = {}  # Key: (Course, University), Value: Row Dict
    fieldnames = []

    if not os.path.exists(csv_path):
        log("CSV not found, skipping tagging.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            key = (row.get("Course"), row.get("University"))
            courses_db[key] = row

    # --- LOOP 1: REQUIREMENTS ---
    log(f"Starting Loop 1: Special Requirements for {level_name}")
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

                                # Special Requirements
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

            # SAVE PROGRESS (After each Requirement)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(courses_db.values())
            log(f"Saved tags for Requirement: {req_name}")

        except Exception as e:
            log(f"Error in Requirement loop for {req_name}: {e}")

    # --- LOOP 2: STUDY AREAS ---
    log(f"Starting Loop 2: Study Areas for {level_name}")
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

            # Click search to close dropdown (and search)
            search_btn = driver.find_element(By.XPATH, SEARCH_BUTTON_XPATH)
            driver.execute_script("arguments[0].click();", search_btn)
            time.sleep(1)

            # Search (No Requirement selected)
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

                                    # Area of Study
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

            # SAVE PROGRESS (After each Study Area)
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


def worker(country_name, selected_levels, layout, progress, page_task, status_table):
    driver = get_driver()
    try:
        login_if_needed(driver)
        setup_search_page(driver, country_name)

        for level in selected_levels:
            status_table["Current Checkbox"] = level
            status_table["Current Study Area"] = "None (Base Scraping)"
            status_table["Current Requirement"] = "None"

            csv_filename = f"{country_name.replace(' ', '_')}.csv"
            csv_path = os.path.join(os.getcwd(), csv_filename)

            # Select Level
            cb = select_program_level(driver, level)
            if not cb:
                continue

            # PHASE 1: BASE SCRAPING
            scrape_base_courses(driver, level, csv_path, progress, page_task)

            # PHASE 2: TAGGING
            tag_courses(driver, level, csv_path, status_table)

            # Deselect Level
            deselect_program_level(driver, cb)

    except Exception as e:
        log(f"Critical Error: {e}")
    finally:
        driver.quit()
        status_table["Status"] = "Finished"


def main():
    console = Console()
    country_name = Prompt.ask(
        "[bold green]Enter Country Name[/bold green]", default="United Kingdom"
    )

    console.print("\n[bold cyan]Available Program Levels:[/bold cyan]")
    for idx, level in enumerate(PROGRAM_LEVELS):
        console.print(f"[{idx + 1}] {level}")

    selection = Prompt.ask(
        "\n[bold green]Select Program Levels (comma-separated indices) or 'all'[/bold green]",
        default="all",
    )

    if selection.lower() == "all":
        selected_levels = PROGRAM_LEVELS
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_levels = [
                PROGRAM_LEVELS[i] for i in indices if 0 <= i < len(PROGRAM_LEVELS)
            ]
        except:
            selected_levels = PROGRAM_LEVELS

    # TUI Setup
    status_table_data = {
        "Country": country_name,
        "Current Checkbox": "Waiting...",
        "Current Study Area": "Waiting...",
        "Current Requirement": "Waiting...",
        "Status": "Running",
    }

    def generate_status_table():
        table = Table(title="Smart Scraper Status", expand=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in status_table_data.items():
            table.add_row(k, v)
        return table

    layout = Layout()
    layout.split(Layout(name="header", size=12), Layout(name="body", ratio=1))

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
    )
    page_task = progress.add_task("Pages", total=100)

    t = threading.Thread(
        target=worker,
        args=(
            country_name,
            selected_levels,
            layout,
            progress,
            page_task,
            status_table_data,
        ),
    )
    t.start()

    with Live(layout, refresh_per_second=4, screen=True, console=console) as live:
        while t.is_alive():
            layout["header"].update(
                Panel(
                    Group(generate_status_table(), progress),
                    title="Dashboard",
                    border_style="blue",
                )
            )

            console_height = live.console.height
            available_height = max(5, console_height - 14)
            with log_lock:
                log_content = "\n".join(logs[-available_height:])
            layout["body"].update(Panel(log_content, title="Log", border_style="green"))
            time.sleep(0.2)


if __name__ == "__main__":
    main()
