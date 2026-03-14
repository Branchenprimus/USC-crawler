import glob
import re
import csv
import os

def clean_text(text):
    if not text:
        return "N/A"
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", "\"").replace("&lt;", "<").replace("&gt;", ">")
    return " ".join(text.split())

def extract_content(pattern, text, default="N/A"):
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return clean_text(match.group(1))
    return default

def extract_venue_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    name = extract_content(r'<h1[^>]*>(.*?)</h1>', content)
    rating = extract_content(r'<span class="rating__score">(.*?)</span>', content)
    disciplines = extract_content(r'<div class="disciplines">(.*?)</div>', content)
    
    description_block = re.search(r'<p class="description">(.*?)</p>', content, re.DOTALL)
    description = clean_text(description_block.group(1)) if description_block else "N/A"
        
    address = "N/A"
    address_match = re.search(r'class="usc-map-marker"[^>]*data-full-address="([^"]*)"', content)
    if address_match:
        address = address_match.group(1)
    
    if address == "N/A":
        street = extract_content(r'"streetAddress":\s*"([^"]*)"', content, "")
        locality = extract_content(r'"addressLocality":\s*"([^"]*)"', content, "")
        if street or locality:
            address = f"{street}, {locality}".strip(", ")

    usc_url = extract_content(r'<link rel="canonical" href="([^"]*)"', content, "N/A")
    
    website = "N/A"
    website_section_match = re.search(r'<h2>Webseite:</h2>(.*?)</div>', content, re.DOTALL)
    if website_section_match:
        href_match = re.search(r'href="([^"]*)"', website_section_match.group(1))
        if href_match:
            website = href_match.group(1)

    return {
        "Name": name,
        "Rating": rating,
        "Disciplines": disciplines,
        "Description": description,
        "Address": address,
        "Website": website,
        "USC_URL": usc_url
    }

def extract_class_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    name = extract_content(r'<h3>(.*?)</h3>', content, "N/A")
    datetime_str = extract_content(r'<p class="smm-class-details__datetime">(.*?)</p>', content, "N/A")
    
    cat_match = re.search(r'<span class="smm-class-details__icon disciplines"></span>\s*(.*?)\s*</p>', content, re.DOTALL)
    category = clean_text(cat_match.group(1)) if cat_match else "N/A"
    
    duration = "N/A"
    spots = "N/A"
    
    desc_match = re.search(r'class="smm-class-details__pre-line class-description">\s*(.*?)\s*</span>', content, re.DOTALL)
    description = clean_text(desc_match.group(1)) if desc_match else "N/A"
    
    venue_match = re.search(r'<span class="smm-class-details__icon full-address"></span>\s*(.*?)\s*</p>', content, re.DOTALL)
    venue_name = clean_text(venue_match.group(1)) if venue_match else "N/A"

    return {
        "Name": name,
        "Date_Time": datetime_str,
        "Category": category,
        "Duration": duration,
        "Spots": spots,
        "Description": description,
        "Venue": venue_name
    }

def process_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    venue_map = {}
    
    # Process Venues first to map them
    venues_dir = os.path.join(input_dir, "venues")
    if os.path.exists(venues_dir):
        html_files = glob.glob(os.path.join(venues_dir, "venue_*.html"))
        html_files.sort()
        print(f"Processing {len(html_files)} venue files...")
        for i, file_path in enumerate(html_files):
            if i > 0 and i % 50 == 0:
                print(f"Processed {i}/{len(html_files)} venues...", end="\r")
            try:
                venue_info = extract_venue_data(file_path)
                # Parse out the core name from the url to map correctly, or match on name.
                # Actually, the Class "Venue" string often includes city/address. 
                # Let's clean the Class Venue string or just map by the exact "Name" field.
                venue_map[venue_info["Name"]] = venue_info
            except Exception as e:
                print(f"\nError processing {file_path}: {e}")
                
    all_data = []

    # Process Classes
    classes_dir = os.path.join(input_dir, "classes")
    if os.path.exists(classes_dir):
        class_files = glob.glob(os.path.join(classes_dir, "class_*.html"))
        class_files.sort()
        print(f"\nProcessing {len(class_files)} class files...")
        for i, file_path in enumerate(class_files):
            if i > 0 and i % 50 == 0:
                print(f"Processed {i}/{len(class_files)} classes...", end="\r")
            try:
                c_info = extract_class_data(file_path)
                
                # The trailing part of the Class venue string may contain the address. 
                # We attempt to find the matching venue by fuzzy matching the string.
                matched_venue = None
                class_venue_base = c_info["Venue"].split(',')[0].strip()
                
                # Check for an exact substring match first
                for v_name, v_data in venue_map.items():
                    if class_venue_base.lower() in v_name.lower() or v_name.lower() in class_venue_base.lower():
                        matched_venue = v_data
                        break
                        
                # If exact substring doesn't work, try difflib for closest string match
                if not matched_venue:
                    import difflib
                    all_venue_names = list(venue_map.keys())
                    matches = difflib.get_close_matches(class_venue_base, all_venue_names, n=1, cutoff=0.4)
                    if matches:
                        matched_venue = venue_map[matches[0]]
                
                # Default empty venue fields if no match
                if not matched_venue:
                    matched_venue = {
                        "Name": c_info["Venue"],
                        "Rating": "N/A",
                        "Disciplines": "N/A",
                        "Address": "N/A",
                        "Description": "N/A"
                    }

                all_data.append({
                    "Class Title": c_info["Name"],
                    "Class Date": c_info["Date_Time"],
                    "Class Category": c_info["Category"],
                    "Class Description": c_info["Description"],
                    "Venue Name": matched_venue["Name"],
                    "Venue Rating": matched_venue["Rating"],
                    "Venue Disciplines": matched_venue["Disciplines"],
                    "Venue Address": matched_venue["Address"],
                    "Venue Description": matched_venue["Description"]
                })
            except Exception as e:
                print(f"\nError processing {file_path}: {e}")
                
    if all_data:
        unified_file = os.path.join(output_dir, "data.csv")
        csv_columns = [
            "Class Title", "Class Date", "Class Category", "Class Description",
            "Venue Name", "Venue Rating", "Venue Disciplines", "Venue Address", "Venue Description"
        ]
        try:
            with open(unified_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                for row in all_data:
                    writer.writerow(row)
            print(f"\nSuccessfully wrote {len(all_data)} joined class entries to {unified_file}")
        except IOError as e:
            print(f"\nI/O error: {e}")
            
    return True
