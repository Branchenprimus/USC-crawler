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
    
    name = extract_content(r'<h1>(.*?)</h1>', content)
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

def process_directory(input_dir, output_file):
    html_files = glob.glob(os.path.join(input_dir, "venue_*.html"))
    html_files.sort()
    
    data = []
    print(f"Processing {len(html_files)} files in {input_dir}...")
    for i, file_path in enumerate(html_files):
        if i % 50 == 0:
            print(f"Processed {i}/{len(html_files)}...", end="\r")
        try:
            venue_info = extract_venue_data(file_path)
            data.append(venue_info)
        except Exception as e:
            print(f"\nError processing {file_path}: {e}")
    
    print(f"Processed {len(html_files)}/{len(html_files)}. Writing to CSV...")

    if not data:
        print("No valid data extracted.")
        return False

    csv_columns = ["Name", "Rating", "Disciplines", "Description", "Address", "Website", "USC_URL"]
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"Successfully wrote {len(data)} venues to {output_file}")
        return True
    except IOError as e:
        print(f"I/O error: {e}")
        return False
