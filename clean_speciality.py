import csv
import shutil
import os

def clean_speciality_column(filepath):
    """Remove specific keywords from the Speciality column."""
    
    keywords_to_remove = {
        "speed", "attractions", "mintmark", "restore_page", "how_to_reg", "paid"
    }
    
    print(f"Cleaning Speciality column in {filepath}...")
    
    # Create backup
    backup_file = filepath + ".bak_clean"
    print(f"Creating backup to {backup_file}...")
    shutil.copy2(filepath, backup_file)
    
    temp_file = filepath + ".tmp_clean"
    updated_count = 0
    total_count = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f_in, \
             open(temp_file, 'w', encoding='utf-8', newline='') as f_out:
            
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                total_count += 1
                speciality_str = row.get('Speciality', '')
                
                if speciality_str:
                    # Replace newlines with commas to handle multi-line cells
                    speciality_str = speciality_str.replace('\n', ',')
                    
                    # Split by comma, strip whitespace
                    items = [item.strip() for item in speciality_str.split(',')]
                    
                    # Filter out unwanted keywords (case-insensitive check)
                    cleaned_items = []
                    for item in items:
                        if not item:
                            continue
                        
                        # Check if the item is exactly one of the keywords (case-insensitive)
                        if item.lower() in keywords_to_remove:
                            continue
                            
                        # Also check if the item *contains* the keyword if it's a weird artifact?
                        # User said "contain the text", but usually these are tags.
                        # Let's stick to exact match of the tag first, but since I saw "speed\nFaster...",
                        # splitting by newline first should isolate "speed".
                        
                        cleaned_items.append(item)
                    
                    new_speciality_str = ", ".join(cleaned_items)
                    
                    if new_speciality_str != row.get('Speciality', ''): # Compare with original
                        row['Speciality'] = new_speciality_str
                        updated_count += 1
                
                writer.writerow(row)
                
        # Replace original file
        os.replace(temp_file, filepath)
        print(f"Cleaning complete. Updated {updated_count} out of {total_count} rows.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    target_csv = "data/combined_courses.csv"
    clean_speciality_column(target_csv)
