import csv
import shutil
import os

def add_pgwp_eligibility(filepath):
    """
    Checks 'remarks' column in the CSV.
    If it contains "THIS PROGRAM IS ELIGIBLE FOR PGWP", set 'PGWP eligible' to 'yes', else 'no'.
    """
    
    print(f"Processing {filepath}...")
    
    # Create backup
    backup_file = filepath + ".bak_pgwp"
    print(f"Creating backup to {backup_file}...")
    shutil.copy2(filepath, backup_file)
    
    temp_file = filepath + ".tmp_pgwp"
    updated_count = 0
    total_count = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f_in, \
             open(temp_file, 'w', encoding='utf-8', newline='') as f_out:
            
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            # Add new column if not exists
            if 'PGWP eligible' not in fieldnames:
                fieldnames.append('PGWP eligible')
            
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                total_count += 1
                remarks = row.get('Remarks', '')
                
                # Check for the specific phrase
                if remarks and "THIS PROGRAM IS ELIGIBLE FOR PGWP" in remarks:
                    row['PGWP eligible'] = 'yes'
                    updated_count += 1
                else:
                    row['PGWP eligible'] = 'no'
                
                writer.writerow(row)
                
        # Replace original file
        os.replace(temp_file, filepath)
        print(f"Processing complete. Marked {updated_count} rows as eligible out of {total_count} total rows.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    target_csv = "data/combined_courses.csv"
    if os.path.exists(target_csv):
        add_pgwp_eligibility(target_csv)
    else:
        print(f"Error: {target_csv} does not exist.")
