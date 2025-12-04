import os
import glob
import pandas as pd
from rich.console import Console

# --- Configuration ---
LOCAL_DATA_FOLDER = "data"
OUTPUT_FILE = os.path.join(LOCAL_DATA_FOLDER, "combined_courses.csv")

console = Console()

def combine_csvs():
    """Combines all CSV files in the data folder into one."""
    
    # Find all CSV files
    csv_files = glob.glob(os.path.join(LOCAL_DATA_FOLDER, "*.csv"))
    
    # Filter out the output file itself if it exists
    csv_files = [f for f in csv_files if f != OUTPUT_FILE]
    
    if not csv_files:
        console.print(f"[bold red]No CSV files found in '{LOCAL_DATA_FOLDER}'.[/bold red]")
        return

    console.print(f"[cyan]Found {len(csv_files)} CSV files to combine.[/cyan]")
    
    combined_df = pd.DataFrame()
    files_processed = 0
    
    for file in csv_files:
        try:
            # Read CSV
            df = pd.read_csv(file)
            
            # Add a column for source filename (optional, but often useful)
            # df['Source_File'] = os.path.basename(file)
            
            # Concatenate
            combined_df = pd.concat([combined_df, df], ignore_index=True)
            files_processed += 1
            console.print(f"[green]Processed: {os.path.basename(file)} ({len(df)} rows)[/green]")
            
        except Exception as e:
            console.print(f"[bold red]Error reading {file}: {e}[/bold red]")

    if not combined_df.empty:
        try:
            combined_df.to_csv(OUTPUT_FILE, index=False)
            console.print(f"\n[bold green]Successfully combined {files_processed} files into '{OUTPUT_FILE}'[/bold green]")
            console.print(f"[bold cyan]Total Rows: {len(combined_df)}[/bold cyan]")
        except Exception as e:
            console.print(f"[bold red]Error saving combined file: {e}[/bold red]")
    else:
        console.print("[yellow]No data was combined.[/yellow]")

if __name__ == "__main__":
    combine_csvs()
