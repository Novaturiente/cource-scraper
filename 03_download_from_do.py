import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

# --- Configuration ---
DO_SPACES_ENDPOINT = "https://blr1.digitaloceanspaces.com"
DO_SPACES_REGION = "blr1"
DO_SPACES_BUCKET = "eecglobal"
DO_SPACES_ACCESS_KEY = "DO00G9GPY76L9LEYA637"
DO_SPACES_SECRET_KEY = "J2XtD+McwjA/NZp46HBPmlnV9rPpDXCEa0VB0xYZ+gA"
DO_SPACES_FOLDER = "Scrapes"
LOCAL_DATA_FOLDER = "data"

console = Console()

def ensure_data_folder(subfolder=None):
    """Creates the data folder (and subfolder) if it doesn't exist."""
    path = LOCAL_DATA_FOLDER
    if subfolder:
        path = os.path.join(LOCAL_DATA_FOLDER, subfolder)
    
    if not os.path.exists(path):
        os.makedirs(path)
        console.print(f"[green]Created local folder: {path}[/green]")
    return path

def get_remote_csv_files(client, subfolder=None):
    """Lists CSV files in the DO Spaces folder (or subfolder)."""
    prefix = DO_SPACES_FOLDER
    if subfolder:
        prefix = f"{DO_SPACES_FOLDER}/{subfolder}"
        
    # Add trailing slash if not present to ensure we look inside the folder
    if not prefix.endswith('/'):
        prefix += '/'

    try:
        response = client.list_objects_v2(Bucket=DO_SPACES_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            return []
        
        files = []
        for obj in response['Contents']:
            key = obj['Key']
            # Filter for CSVs and ensure we don't pick up the folder itself or files in nested sub-subfolders if we only want one level
            # For now, let's just get all CSVs under that prefix
            if key.endswith('.csv'):
                files.append({'key': key, 'size': obj['Size']})
        return files
    except ClientError as e:
        console.print(f"[bold red]Error listing files: {e}[/bold red]")
        return []

def download_files():
    """Downloads all CSV files from DO Spaces to the local data folder."""
    session = boto3.session.Session()
    client = session.client('s3',
                            region_name=DO_SPACES_REGION,
                            endpoint_url=DO_SPACES_ENDPOINT,
                            aws_access_key_id=DO_SPACES_ACCESS_KEY,
                            aws_secret_access_key=DO_SPACES_SECRET_KEY)

    console.print("[bold cyan]DigitalOcean Spaces Downloader[/bold cyan]")
    subfolder = Prompt.ask("[bold yellow]Enter subfolder name to download from (leave empty for root)[/bold yellow]", default="")

    local_target_dir = ensure_data_folder(subfolder if subfolder else None)
    
    console.print(f"[cyan]Fetching file list from DigitalOcean Spaces ({'root' if not subfolder else subfolder})...[/cyan]")
    files = get_remote_csv_files(client, subfolder if subfolder else None)
    
    if not files:
        console.print("[yellow]No CSV files found in the remote folder.[/yellow]")
        return

    console.print(f"[green]Found {len(files)} CSV files. Starting download to '{local_target_dir}'...[/green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task("Overall Progress", total=len(files))
        
        for file_info in files:
            key = file_info['key']
            file_name = os.path.basename(key)
            local_path = os.path.join(local_target_dir, file_name)
            file_size = file_info['size']
            
            download_task = progress.add_task(f"Downloading {file_name}", total=file_size)
            
            try:
                client.download_file(
                    DO_SPACES_BUCKET, 
                    key, 
                    local_path,
                    Callback=lambda bytes_transferred: progress.update(download_task, advance=bytes_transferred)
                )
                progress.update(download_task, completed=file_size) # Ensure 100% on completion
                progress.remove_task(download_task) # Remove individual file task when done to keep UI clean
                
            except Exception as e:
                console.print(f"[bold red]Failed to download {file_name}: {e}[/bold red]")
            
            progress.advance(overall_task)

    console.print(f"[bold green]Download complete! Files saved to '{local_target_dir}' folder.[/bold green]")

if __name__ == "__main__":
    download_files()
