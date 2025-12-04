import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# --- Configuration ---
DO_SPACES_ENDPOINT = "https://blr1.digitaloceanspaces.com"
DO_SPACES_REGION = "blr1"
DO_SPACES_BUCKET = "eecglobal"
DO_SPACES_ACCESS_KEY = "DO00G9GPY76L9LEYA637"
DO_SPACES_SECRET_KEY = "J2XtD+McwjA/NZp46HBPmlnV9rPpDXCEa0VB0xYZ+gA"
DO_SPACES_FOLDER = "Scrapes"

console = Console()

def get_csv_files():
    """Returns a list of .csv files in the current directory."""
    files = [f for f in os.listdir('.') if f.endswith('.csv') and os.path.isfile(f)]
    files.sort()
    return files

def select_file(files):
    """Displays files and prompts user for selection."""
    if not files:
        console.print("[bold red]No CSV files found in the current directory.[/bold red]")
        return None

    table = Table(title="Available CSV Files")
    table.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table.add_column("Filename", style="magenta")
    table.add_column("Size (KB)", justify="right", style="green")

    for idx, file in enumerate(files):
        size_kb = os.path.getsize(file) / 1024
        table.add_row(str(idx + 1), file, f"{size_kb:.2f}")

    console.print(table)

    while True:
        selection = Prompt.ask("[bold yellow]Select a file number to upload[/bold yellow]", default="1")
        try:
            index = int(selection) - 1
            if 0 <= index < len(files):
                return files[index]
            else:
                console.print("[bold red]Invalid selection. Please try again.[/bold red]")
        except ValueError:
            console.print("[bold red]Please enter a valid number.[/bold red]")

def upload_to_spaces(file_path):
    """Uploads the file to DigitalOcean Spaces."""
    session = boto3.session.Session()
    client = session.client('s3',
                            region_name=DO_SPACES_REGION,
                            endpoint_url=DO_SPACES_ENDPOINT,
                            aws_access_key_id=DO_SPACES_ACCESS_KEY,
                            aws_secret_access_key=DO_SPACES_SECRET_KEY)

    file_name = os.path.basename(file_path)
    object_name = f"{DO_SPACES_FOLDER}/{file_name}"

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description=f"Uploading {file_name}...", total=None)
            
            # Upload the file
            client.upload_file(file_path, DO_SPACES_BUCKET, object_name, ExtraArgs={'ACL': 'public-read'})
            
        console.print(f"[bold green]Successfully uploaded {file_name} to {DO_SPACES_BUCKET}/{object_name}[/bold green]")
        
        # Construct public URL (assuming public-read)
        public_url = f"{DO_SPACES_ENDPOINT.replace('https://', f'https://{DO_SPACES_BUCKET}.')}/{object_name}"
        console.print(f"[bold blue]Public URL:[/bold blue] {public_url}")

    except FileNotFoundError:
        console.print(f"[bold red]The file {file_path} was not found.[/bold red]")
    except NoCredentialsError:
        console.print("[bold red]Credentials not available.[/bold red]")
    except ClientError as e:
        console.print(f"[bold red]Client error: {e}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")

def main():
    console.print("[bold cyan]DigitalOcean Spaces Uploader[/bold cyan]")
    
    files = get_csv_files()
    selected_file = select_file(files)
    
    if selected_file:
        if Prompt.ask(f"Are you sure you want to upload [bold magenta]{selected_file}[/bold magenta]?", choices=["y", "n"], default="y") == "y":
            upload_to_spaces(selected_file)
        else:
            console.print("[yellow]Upload cancelled.[/yellow]")

if __name__ == "__main__":
    main()
