import os
import pandas as pd
from rich.console import Console
from rich.prompt import Prompt

# --- Configuration ---
LOCAL_DATA_FOLDER = "data"
INPUT_FILE = os.path.join(LOCAL_DATA_FOLDER, "combined_courses.csv")
OUTPUT_FILE = INPUT_FILE

console = Console()

def remove_duplicates():
    """Removes duplicate rows from the combined CSV file based on Course URL."""
    
    if not os.path.exists(INPUT_FILE):
        console.print(f"[bold red]Input file '{INPUT_FILE}' not found.[/bold red]")
        return

    console.print(f"[cyan]Reading '{INPUT_FILE}'...[/cyan]")
    
    try:
        df = pd.read_csv(INPUT_FILE)
        total_rows = len(df)
        console.print(f"[bold blue]Total rows: {total_rows}[/bold blue]")
        
        # Check for duplicates based on 'Course URL'
        if 'Course URL' not in df.columns:
            console.print("[bold red]Column 'Course URL' not found in CSV.[/bold red]")
            return

        duplicates = df[df.duplicated(subset=['Course URL'], keep='first')]
        num_duplicates = len(duplicates)
        
        if num_duplicates == 0:
            console.print("[bold green]No duplicates found based on Course URL.[/bold green]")
            # Optionally save it anyway or just exit
            return

        console.print(f"[bold yellow]Found {num_duplicates} duplicate rows based on 'Course URL'.[/bold yellow]")
        
        # Ask for confirmation
        confirm = Prompt.ask(
            f"Do you want to remove these {num_duplicates} duplicates?", 
            choices=["y", "n"], 
            default="n"
        )
        
        if confirm == "y":
            df_cleaned = df.drop_duplicates(subset=['Course URL'], keep='first')
            cleaned_rows = len(df_cleaned)
            
            console.print(f"[bold green]Removed {num_duplicates} duplicates.[/bold green]")
            console.print(f"[bold blue]Rows remaining: {cleaned_rows}[/bold blue]")
            
            # Save cleaned file
            df_cleaned.to_csv(OUTPUT_FILE, index=False)
            console.print(f"\n[bold green]Successfully saved cleaned data to '{OUTPUT_FILE}'[/bold green]")
        else:
            console.print("[yellow]Operation cancelled. No changes made.[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")

if __name__ == "__main__":
    remove_duplicates()
