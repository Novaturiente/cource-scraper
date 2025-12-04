import os
import pandas as pd
import numpy as np
from rich.console import Console
from rich.prompt import Prompt, IntPrompt

# --- Configuration ---
LOCAL_DATA_FOLDER = "data"
SPLIT_FOLDER = "split"
RAW_FILE = os.path.join(LOCAL_DATA_FOLDER, "combined_courses.csv")

console = Console()

def split_csv():
    """Splits the combined CSV file into N parts."""
    
    # Determine input file
    if os.path.exists(RAW_FILE):
        input_file = RAW_FILE
        console.print(f"[cyan]Using file: {RAW_FILE}[/cyan]")
    else:
        console.print(f"[bold red]No input CSV file found in '{LOCAL_DATA_FOLDER}'.[/bold red]")
        return

    # Read DataFrame
    try:
        df = pd.read_csv(input_file)
        total_rows = len(df)
        console.print(f"[bold blue]Total rows loaded: {total_rows}[/bold blue]")
    except Exception as e:
        console.print(f"[bold red]Error reading file: {e}[/bold red]")
        return

    # Ask for number of splits
    num_splits = IntPrompt.ask(
        "[bold green]Enter the number of files to split into[/bold green]", 
        default=2
    )
    
    if num_splits <= 0:
        console.print("[bold red]Number of splits must be greater than 0.[/bold red]")
        return

    # Create split directory
    if not os.path.exists(SPLIT_FOLDER):
        os.makedirs(SPLIT_FOLDER)
        console.print(f"[green]Created split directory: {SPLIT_FOLDER}[/green]")

    # Split
    try:
        splits = np.array_split(df, num_splits)
        
        console.print(f"\n[cyan]Splitting into {num_splits} files...[/cyan]")
        
        for i, split_df in enumerate(splits):
            part_num = i + 1
            input_basename = os.path.basename(input_file)
            output_filename = f"{part_num}_{input_basename}"
            output_path = os.path.join(SPLIT_FOLDER, output_filename)
            
            split_df.to_csv(output_path, index=False)
            console.print(f"  - Saved [bold magenta]{output_filename}[/bold magenta] ({len(split_df)} rows)")
            
        console.print(f"\n[bold green]Successfully split into {num_splits} files in '{SPLIT_FOLDER}'[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error during splitting: {e}[/bold red]")

if __name__ == "__main__":
    split_csv()
