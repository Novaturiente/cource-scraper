import csv
import shutil
import os

def normalize_key(text):
    """Normalize text for key generation."""
    if not text:
        return ""
    return text.strip().lower()

def load_canada_data(filepath):
    """Load canada.csv data into a dictionary."""
    data_map = {}
    print(f"Loading data from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Key: (Program Level, Course, University)
                key = (
                    normalize_key(row.get('Program Level')),
                    normalize_key(row.get('Course')),
                    normalize_key(row.get('University'))
                )
                # Store the whole row or just the fields we need
                data_map[key] = {
                    'Speciality': row.get('Speciality', ''),
                    'Rankings': row.get('Rankings', ''),
                    'Yearly Tuition Fee': row.get('Yearly Tuition Fee', ''),
                    'Application Fee': row.get('Application Fee', '')
                }
        print(f"Loaded {len(data_map)} entries from {filepath}.")
        return data_map
    except FileNotFoundError:
        print(f"Error: {filepath} not found.")
        return {}

def merge_data(source_file, target_file):
    """Merge data from source_file (canada.csv) into target_file."""
    
    canada_data = load_canada_data(source_file)
    if not canada_data:
        return

    # Create a backup of the target file
    backup_file = target_file + ".bak"
    print(f"Creating backup of {target_file} to {backup_file}...")
    shutil.copy2(target_file, backup_file)

    temp_file = target_file + ".tmp"
    updated_count = 0
    total_count = 0

    print(f"Processing {target_file}...")
    
    try:
        with open(target_file, 'r', encoding='utf-8') as f_in, \
             open(temp_file, 'w', encoding='utf-8', newline='') as f_out:
            
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            # Ensure all target columns exist in fieldnames
            target_columns = ['Speciality', 'Rankings', 'Yearly Tuition Fee', 'Application Fee']
            for col in target_columns:
                if col not in fieldnames:
                    fieldnames.append(col)
            
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                total_count += 1
                key = (
                    normalize_key(row.get('Program Level')),
                    normalize_key(row.get('Course')),
                    normalize_key(row.get('University'))
                )

                if key in canada_data:
                    source_row = canada_data[key]
                    # Update fields
                    row['Speciality'] = source_row['Speciality']
                    row['Rankings'] = source_row['Rankings']
                    row['Yearly Tuition Fee'] = source_row['Yearly Tuition Fee']
                    row['Application Fee'] = source_row['Application Fee']
                    updated_count += 1
                
                writer.writerow(row)

        # Replace original file with updated file
        os.replace(temp_file, target_file)
        print(f"Merge complete. Updated {updated_count} out of {total_count} rows.")
        print(f"Updated file saved to {target_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    source_csv = "canada.csv"
    target_csv = "data/combined_courses.csv"
    
    merge_data(source_csv, target_csv)
