import csv
import os
import time
import hashlib
import requests
import boto3
import threading
import queue
from botocore.client import Config

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group, Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt

# DigitalOcean Spaces Configuration
DO_SPACES_ENDPOINT = "https://blr1.digitaloceanspaces.com"
DO_SPACES_REGION = "blr1"
DO_SPACES_BUCKET = "eecglobal"
DO_SPACES_ACCESS_KEY = "DO00G9GPY76L9LEYA637"
DO_SPACES_SECRET_KEY = "J2XtD+McwjA/NZp46HBPmlnV9rPpDXCEa0VB0xYZ+gA"
DO_SPACES_FOLDER = "university-logos"

# Input Configuration
INPUT_CSV_FILENAME = "canada-courses-2026.csv"

# Initialize DigitalOcean Spaces client
s3_client = boto3.client(
    's3',
    region_name=DO_SPACES_REGION,
    endpoint_url=DO_SPACES_ENDPOINT,
    aws_access_key_id=DO_SPACES_ACCESS_KEY,
    aws_secret_access_key=DO_SPACES_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

def download_and_upload_logo(image_url, university_name):
    """
    Downloads an image from the given URL and uploads it to DigitalOcean Spaces.
    Returns the permanent public URL of the uploaded image.
    """
    try:
        # Download the image first
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image_content = response.content
        
        # Generate a unique filename based on university name and IMAGE CONTENT hash
        safe_name = "".join(c for c in university_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '-').lower()
        
        # Hash the actual image content (not the URL) to ensure same image = same hash
        content_hash = hashlib.md5(image_content).hexdigest()[:8]
        
        # Extract file extension from URL (default to .jpg if not found)
        file_ext = '.jpg'
        if '.' in image_url.split('?')[0]:  # Check before query params
            ext_candidate = image_url.split('?')[0].split('.')[-1].lower()
            if ext_candidate in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
                file_ext = f'.{ext_candidate}'
        
        filename = f"{safe_name}-{content_hash}{file_ext}"
        s3_key = f"{DO_SPACES_FOLDER}/{filename}"
        
        # Check if file already exists to avoid re-uploading
        try:
            s3_client.head_object(Bucket=DO_SPACES_BUCKET, Key=s3_key)
            # File exists, return existing URL
            public_url = f"{DO_SPACES_ENDPOINT}/{DO_SPACES_BUCKET}/{s3_key}"
            # print(f"    ℹ️  Logo already exists, using existing file")
            return public_url
        except:
            # File doesn't exist, upload it
            pass
        
        # Upload to DigitalOcean Spaces
        s3_client.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=s3_key,
            Body=image_content,
            ACL='public-read',  # Make the file publicly accessible
            ContentType=response.headers.get('Content-Type', 'image/jpeg')
        )
        
        # Generate the public URL
        public_url = f"{DO_SPACES_ENDPOINT}/{DO_SPACES_BUCKET}/{s3_key}"
        
        return public_url
        
    except Exception as e:
        print(f"    ⚠ Error downloading/uploading logo: {str(e)[:100]}")
        return None

def worker_task(worker_id, url_queue, csv_lock, fieldnames, processed_rows_list, dynamic_columns, output_path, header_written_container, driver_path, log_queue, worker_status):
    """
    Worker function to process URLs from the queue.
    """
    """
    Worker function to process URLs from the queue.
    """
    log_queue.put(f"[Worker {worker_id}] Starting...")
    worker_status[worker_id] = "Starting..."

    # Setup Chrome options for this worker
    options = Options()
    # Use a unique profile directory for each worker to avoid conflicts
    profile_dir = os.path.join(os.environ.get("TEMP_DIR", "."), f"chrome_profile_{worker_id}")
    options.add_argument(f"user-data-dir={profile_dir}")
    options.page_load_strategy = 'none'
    # options.add_argument("--headless") # Uncomment for headless execution

    # Configure ChromeDriver logging
    log_path = os.path.join(os.environ.get("TEMP_DIR", "."), f"chromedriver_{worker_id}.log")
    service = ChromeService(
        executable_path=driver_path,
        service_args=["--verbose", f"--log-path={log_path}"],
    )

    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 1. Login
        # 1. Login
        log_queue.put(f"[Worker {worker_id}] Navigating to Dashboard for login...")
        worker_status[worker_id] = "Logging in..."
        driver.get("https://www.coursefinder.ai/Dashboard")
        time.sleep(3)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'Logout')]"))
            )
            log_queue.put(f"[Worker {worker_id}] Already logged in.")
        except:
            log_queue.put(f"[Worker {worker_id}] Performing login...")
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

                login_button.click()

                log_queue.put(f"[Worker {worker_id}] Login submitted.")
                time.sleep(5)
            except Exception as e:
                log_queue.put(f"[Worker {worker_id}] Login failed: {e}")
                worker_status[worker_id] = "Login Failed"
                return # Exit worker if login fails

        # 2. Process Queue
        while not url_queue.empty():
            try:
                row_data = url_queue.get_nowait()
            except queue.Empty:
                break

            course_url = row_data["url"]
            row_number = row_data["row_number"]
            original_row = row_data["row"]

            course_url = row_data["url"]
            row_number = row_data["row_number"]
            original_row = row_data["row"]

            log_queue.put(f"[Worker {worker_id}] Processing Row {row_number}")
            worker_status[worker_id] = f"Row {row_number}"

            columns_changed = False

            try:
                driver.get(course_url)
                
                try:
                    # Wait specifically for the College Logo to be present
                    # This indicates the critical top section is loaded
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#divContentCourse > div > div.col-xl-3.col-lg-4.col-sm-12 > div.un-wrap.mb-m-10 > div.row.unlogo > img"))
                    )
                    
                    # Optional: Wait a split second for layout to settle
                    time.sleep(0.5)
                    
                    # Stop further loading (ads, trackers, etc.) to save time
                    driver.execute_script("window.stop();")
                    
                except Exception as e:
                    # If logo wait fails, we might still have partial content, so we just log and continue
                    # hoping the try-except blocks below catch what they can
                    # If logo wait fails, we might still have partial content, so we just log and continue
                    # hoping the try-except blocks below catch what they can
                    log_queue.put(f"[Worker {worker_id}] ⏳ Timeout waiting for Logo: {e}")
                
                time.sleep(1)

                # --- Extraction Logic (Same as original) ---
                
                # State
                try:
                    state_div = driver.find_element(By.CSS_SELECTOR, "#divContentCourse > div > div.col-xl-3.col-lg-4.col-sm-12 > div.un-wrap.mb-m-10 > div:nth-child(2) > div > div:nth-child(2)")
                    spans = state_div.find_elements(By.TAG_NAME, "span")
                    if len(spans) >= 2:
                        original_row["State"] = spans[1].text.strip()
                    else:
                        original_row["State"] = "Not found"
                except:
                    original_row["State"] = "Not found"

                # College URL
                try:
                    college_link = driver.find_element(By.CSS_SELECTOR, "#divContentCourse > div > div.col-xl-3.col-lg-4.col-sm-12 > div.un-wrap.mb-m-10 > div:nth-child(4) > div > div > a")
                    college_url = college_link.get_attribute("href")
                    original_row["College URL"] = college_url if college_url else "Not found"
                except:
                    original_row["College URL"] = "Not found"

                # College Logo
                try:
                    college_logo_img = driver.find_element(By.CSS_SELECTOR, "#divContentCourse > div > div.col-xl-3.col-lg-4.col-sm-12 > div.un-wrap.mb-m-10 > div.row.unlogo > img")
                    college_logo_temp_url = college_logo_img.get_attribute("src")
                    
                    if college_logo_temp_url:
                        university_name = original_row.get('University', 'unknown-university')
                        permanent_url = download_and_upload_logo(college_logo_temp_url, university_name)
                        original_row["College Logo"] = permanent_url if permanent_url else "Upload failed"
                    else:
                        original_row["College Logo"] = "Not found"
                except:
                    original_row["College Logo"] = "Not found"

                # Dynamic Extraction for Course Details (Campus & URL)
                original_row["Campus"] = "Not found"
                original_row["University Course URL"] = "Not found"
                original_row["Application Deadline"] = "Not found"
                
                try:
                    details_ul = driver.find_element(By.CSS_SELECTOR, "#divMiddle > div.panel.panel-info1.margin-bottom-0 > div.panel.panel-info1.panel-course-details > div.panel-body > ul")
                    detail_items = details_ul.find_elements(By.TAG_NAME, "li")
                    
                    for item in detail_items:
                        try:
                            # Structure: li > div > div (Label), div (Value)
                            # We need to find the inner divs. 
                            # The user said: "multiple li sections each section has a div then inside taht two div"
                            # Let's try to find the direct children divs of the first div inside li
                            
                            # Using xpath to be precise about the structure described
                            # .//div/div[1] -> Label
                            # .//div/div[2] -> Value
                            
                            label_div = item.find_element(By.XPATH, "./div/div[1]")
                            value_div = item.find_element(By.XPATH, "./div/div[2]")
                            
                            label_text = label_div.text.strip().lower()
                            
                            if "campus" in label_text:
                                campus_val = value_div.text.strip()
                                if campus_val:
                                    original_row["Campus"] = campus_val
                                    
                            elif "program url" in label_text or "course url" in label_text:
                                try:
                                    url_link = value_div.find_element(By.TAG_NAME, "a")
                                    url_val = url_link.get_attribute("href")
                                    if url_val:
                                        original_row["University Course URL"] = url_val
                                except:
                                    pass # No link found in this div
                                    
                            elif "application deadline" in label_text:
                                deadline_val = value_div.text.strip()
                                if deadline_val:
                                    original_row["Application Deadline"] = deadline_val
                                    
                        except Exception:
                            continue # Skip this item if structure doesn't match
                            
                except Exception as e:
                    # If the main UL is not found or something else fails, we keep defaults
                    pass

                # Dynamic Table Data (English Tests)
                try:
                    test_table = driver.find_element(By.CSS_SELECTOR, "#divMiddle > div.panel.panel-info1.margin-bottom-0 > div.panel.panel-info1.panel-english-tests > div.panel-body > ul")
                    list_items = test_table.find_elements(By.TAG_NAME, "li")
                    
                    for li in list_items:
                        try:
                            inner_divs = li.find_elements(By.XPATH, "./div/div")
                            if len(inner_divs) >= 2:
                                column_name = inner_divs[0].text.strip()
                                column_value = inner_divs[1].text.strip()
                                
                                if column_name:
                                    # LOCK REQUIRED for checking/updating shared fieldnames
                                    with csv_lock:
                                        if column_name not in fieldnames:
                                            if "More Info" in fieldnames:
                                                more_info_index = fieldnames.index("More Info")
                                                fieldnames.insert(more_info_index, column_name)
                                            else:
                                                fieldnames.append(column_name)
                                            
                                            if column_name not in dynamic_columns:
                                                dynamic_columns.append(column_name)
                                            
                                            columns_changed = True
                                            
                                            columns_changed = True
                                            log_queue.put(f"[Worker {worker_id}] ➕ New column discovered: {column_name}")
                                    
                                    original_row[column_name] = column_value if column_value else "Not found"
                        except:
                            pass
                except:
                    pass

                # Entry Requirements
                try:
                    entry_req_panel = driver.find_element(By.CSS_SELECTOR, "#divMiddle > div.panel.panel-info1.margin-bottom-0 > div.panel.panel-info2.panel-entry-req")
                    entry_req_list = entry_req_panel.find_elements(By.XPATH, ".//div[2]/ul/li/div/div")
                    if entry_req_list:
                        entry_requirements = [item.text.strip() for item in entry_req_list if item.text.strip()]
                        original_row["Entry Requirements"] = " | ".join(entry_requirements)
                    else:
                        original_row["Entry Requirements"] = ""
                except:
                    original_row["Entry Requirements"] = ""

                # Remarks
                try:
                    remarks_panel = driver.find_element(By.CSS_SELECTOR, "#divMiddle > div.panel.panel-info1.margin-bottom-0 > div.panel.panel-info1.panel-remarks")
                    remarks_list = remarks_panel.find_elements(By.XPATH, ".//div[2]/ul/li/div/div")
                    if remarks_list:
                        remarks = [item.text.strip() for item in remarks_list if item.text.strip()]
                        original_row["Remarks"] = " | ".join(remarks)
                    else:
                        original_row["Remarks"] = ""
                except:
                    original_row["Remarks"] = ""

                # Standardized Test Requirements
                try:
                    std_test_panel = driver.find_element(By.CSS_SELECTOR, "#divMiddle > div.panel.panel-info1.margin-bottom-0 > div.panel.panel-info1.panel-standard-tests")
                    std_test_text = std_test_panel.find_element(By.XPATH, ".//div[2]")
                    if std_test_text:
                        original_row["Standardized Test Requirements"] = std_test_text.text.strip()
                    else:
                        original_row["Standardized Test Requirements"] = ""
                except:
                    original_row["Standardized Test Requirements"] = ""

                # Last Updated Date
                try:
                    last_updated_div = driver.find_element(By.CLASS_NAME, "course-last-updated")
                    if last_updated_div:
                        original_row["Last Updated Date"] = last_updated_div.text.strip()
                    else:
                        original_row["Last Updated Date"] = "Not found"
                except:
                    original_row["Last Updated Date"] = "Not found"

                original_row["More Info"] = "yes"
                log_queue.put(f"[Worker {worker_id}] ✓ Finished Row {row_number}")

            except Exception as e:
                log_queue.put(f"[Worker {worker_id}] ⚠ Error loading URL: {e}")

            # --- Writing to CSV (Critical Section) ---
            with csv_lock:
                try:
                    processed_rows_list.append(original_row)
                    
                    # If columns changed OR this is the first write (and header not written), rewrite everything
                    if columns_changed or not header_written_container[0]:
                        log_queue.put(f"[Worker {worker_id}] 📝 Schema changed or new file - Rewriting entire CSV...")
                        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(processed_rows_list)
                        header_written_container[0] = True
                    else:
                        # Append single row
                        with open(output_path, "a", newline="", encoding="utf-8") as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow(original_row)
                        # print(f"[Worker {worker_id}] 💾 Appended row to CSV")
                except Exception as e:
                    log_queue.put(f"[Worker {worker_id}] ⚠ Error saving to CSV: {e}")

            url_queue.task_done()
            time.sleep(1) # Small delay

    except Exception as e:
        log_queue.put(f"[Worker {worker_id}] Critical Error: {e}")
        worker_status[worker_id] = "Error"
    finally:
        driver.quit()
        log_queue.put(f"[Worker {worker_id}] Finished.")
        log_queue.put(f"[Worker {worker_id}] Finished.")
        worker_status[worker_id] = "Finished"

def select_input_file():
    """
    Lists all CSV files in the current directory and prompts the user to select one.
    """
    console = Console()
    csv_files = [f for f in os.listdir("./split") if f.endswith(".csv")]
    
    if not csv_files:
        console.print("[bold red]No CSV files found in the 'split' directory![/bold red]")
        return None

    console.print("\n[bold cyan]Available CSV Files:[/bold cyan]")
    for idx, file in enumerate(csv_files, 1):
        console.print(f"[green]{idx}.[/green] {file}")

    while True:
        try:
            selection = Prompt.ask("\n[bold yellow]Select a file number[/bold yellow]", default="1")
            index = int(selection) - 1
            if 0 <= index < len(csv_files):
                selected_file = csv_files[index]
                console.print(f"[bold green]Selected:[/bold green] {selected_file}\n")
                return selected_file
            else:
                console.print("[bold red]Invalid selection. Please try again.[/bold red]")
        except ValueError:
            console.print("[bold red]Please enter a valid number.[/bold red]")

def main():
    # 0. Select Input File
    selected_csv = select_input_file()
    if not selected_csv:
        return
        
    global INPUT_CSV_FILENAME
    INPUT_CSV_FILENAME = selected_csv

    # Install driver once in the main thread
    print("Installing/Verifying ChromeDriver...")
    driver_path = ChromeDriverManager().install()
    print(f"ChromeDriver path: {driver_path}")

    # 1. Read CSV
    csv_filename = INPUT_CSV_FILENAME
    csv_path = os.path.join(os.getcwd(), "split", csv_filename)

    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    all_rows = []
    fieldnames = []
    
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = list(reader.fieldnames)
        
        if "Course URL" not in fieldnames:
            print("Error: 'Course URL' column not found.")
            return

        for row_number, row in enumerate(reader, start=2):
            url = row.get("Course URL", "").strip()
            if url and url != "Not found":
                all_rows.append({
                    "row_number": row_number,
                    "row": row.copy(),
                    "url": url
                })

    print(f"Found {len(all_rows)} valid course URLs.")

    # 2. Setup Output & Resume
    # 2. Setup Output & Resume
    # Derive output filename from input filename
    base_name = os.path.splitext(INPUT_CSV_FILENAME)[0]
    output_filename = f"{base_name}-with-details.csv"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)
    
    processed_urls = set()
    processed_rows_list = []
    header_written_container = [False] # Use list to make it mutable in threads
    dynamic_columns = []

    # Initialize fieldnames with input columns first
    # But if output exists, we want to respect ITS order for existing columns
    
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as csvfile:
                existing_reader = csv.DictReader(csvfile)
                if existing_reader.fieldnames:
                    # Use the existing file's fieldnames as the BASE to preserve order
                    # This ensures "More Info" stays at the end if it was there
                    # and dynamic columns stay in their correct relative positions
                    saved_fieldnames = list(existing_reader.fieldnames)
                    
                    # Add any INPUT columns that might be missing from the output (unlikely but possible)
                    for col in fieldnames:
                        if col not in saved_fieldnames:
                            saved_fieldnames.append(col)
                    
                    fieldnames = saved_fieldnames
                
                for existing_row in existing_reader:
                    # Filter out empty or invalid rows
                    if not existing_row.get("Course URL") or not existing_row.get("Course URL").strip():
                        continue
                        
                    processed_rows_list.append(existing_row)
                    if existing_row.get("More Info") == "yes":
                        processed_urls.add(existing_row.get("Course URL", "").strip())
            
            # Re-scrape last 10 rows to ensure no missing info from interruptions
            RESCAPE_COUNT = 10
            if len(processed_rows_list) > 0:
                # Determine how many to remove (up to 10, but not more than we have)
                count_to_remove = min(len(processed_rows_list), RESCAPE_COUNT)
                
                # Identify rows to remove
                rows_to_remove = processed_rows_list[-count_to_remove:]
                
                # Remove from processed list
                processed_rows_list = processed_rows_list[:-count_to_remove]
                
                print(f"Removing last {len(rows_to_remove)} rows to re-scrape them...")
                
                # Remove from processed_urls set so they get added to the queue again
                for row in rows_to_remove:
                    url = row.get("Course URL", "").strip()
                    if url in processed_urls:
                        processed_urls.remove(url)
                
                # Rewrite the file immediately to reflect the truncation
                # This prevents duplicates and ensures the file state matches our memory state
                with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(processed_rows_list)
                print(f"Rewrote CSV with {len(processed_rows_list)} rows (truncated).")
            
            header_written_container[0] = True
            print(f"Resuming... {len(processed_urls)} URLs already processed.")
        except Exception as e:
            print(f"Error reading existing output: {e}")

    # Ensure our standard new columns are present
    new_columns = ["State", "College URL", "College Logo", "University Course URL", "Campus", "Entry Requirements", "Remarks", "Standardized Test Requirements", "Application Deadline", "Last Updated Date", "More Info"]
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)
            
    # Re-identify dynamic columns (columns that are not in input and not in standard new_columns)
    # This isn't strictly necessary for the logic but good for tracking
    input_cols_set = set(all_rows[0]['row'].keys()) if all_rows else set()
    std_cols_set = set(new_columns)
    for col in fieldnames:
        if col not in input_cols_set and col not in std_cols_set:
            if col not in dynamic_columns:
                dynamic_columns.append(col)

    # 3. Fill Queue
    url_queue = queue.Queue()
    for row_data in all_rows:
        if row_data["url"] not in processed_urls:
            url_queue.put(row_data)

    print(f"Queue size: {url_queue.qsize()}")

    # 4. Start Threads & TUI
    csv_lock = threading.Lock()
    num_workers = 1
    threads = []
    
    # TUI Setup
    log_queue = queue.Queue()
    worker_status = {}
    for i in range(num_workers):
        worker_status[i+1] = "Initializing"

    def generate_table(worker_status):
        table = Table(title="Worker Status", expand=True)
        table.add_column("Worker ID", style="cyan", width=10)
        table.add_column("Status", style="magenta")
        for wid, status in worker_status.items():
            table.add_row(str(wid), status)
        return table

    def generate_layout():
        layout = Layout()
        layout.split(
            Layout(name="header", size=12),
            Layout(name="body", ratio=1)
        )
        return layout

    layout = generate_layout()
    logs = []
    
    # Progress Bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}")
    )
    task_id = progress.add_task("Scraping...", total=len(all_rows))
    
    # Pre-update progress if resuming
    processed_count = len(processed_urls)
    progress.update(task_id, completed=processed_count)
    
    # Session tracking for ETA
    session_start_time = time.time()
    initial_processed_count = processed_count
    total_urls = len(all_rows)

    # Open log file
    with open("scraper.log", "a", encoding="utf-8") as log_file:
        with Live(layout, refresh_per_second=4, screen=True) as live:
            # Start Workers
            for i in range(num_workers):
                t = threading.Thread(
                    target=worker_task,
                    args=(i+1, url_queue, csv_lock, fieldnames, processed_rows_list, dynamic_columns, output_path, header_written_container, driver_path, log_queue, worker_status)
                )
                t.start()
                threads.append(t)
                time.sleep(2) # Stagger start

            while any(t.is_alive() for t in threads) or not url_queue.empty():
                # Process logs
                while not log_queue.empty():
                    try:
                        msg = log_queue.get_nowait()
                        logs.append(msg)
                        # Write to file
                        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
                        log_file.flush() # Ensure it's written immediately
                        
                        # Keep a reasonable buffer in memory for the TUI
                        if len(logs) > 500: 
                            logs.pop(0)
                    except queue.Empty:
                        break
                
                # Update Progress
                current_processed = len(processed_rows_list)
                progress.update(task_id, completed=current_processed)
                
                # Calculate ETA
                processed_in_session = current_processed - initial_processed_count
                eta_text = "Calculating ETA..."
                
                if processed_in_session > 0:
                    elapsed_time = time.time() - session_start_time
                    avg_time_per_url = elapsed_time / processed_in_session
                    remaining_urls = total_urls - current_processed
                    if remaining_urls > 0:
                        eta_seconds = avg_time_per_url * remaining_urls
                        eta_hours = int(eta_seconds // 3600)
                        eta_minutes = int((eta_seconds % 3600) // 60)
                        eta_text = f"Estimated Time to Finish: {eta_hours} hours : {eta_minutes} minutes"
                    else:
                        eta_text = "Finishing up..."

                # Update Layout
                layout["header"].update(
                    Panel(
                        Group(
                            Text(eta_text, style="bold yellow", justify="center"),
                            progress,
                            generate_table(worker_status)
                        ),
                        title="Scraper Dashboard",
                        border_style="blue"
                    )
                )
                
                # Dynamic Scrolling Logic
                # Calculate available height for logs
                console_height = live.console.height
                header_height = 16 # Approximate height of header panel
                available_height = max(5, console_height - header_height - 2) # -2 for borders
                
                # Slice logs to show only what fits, prioritizing the NEWEST
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

    print("All workers finished.")

if __name__ == "__main__":
    main()
