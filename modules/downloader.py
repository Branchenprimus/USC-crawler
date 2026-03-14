import os
import time
import urllib.request
import sys
import concurrent.futures

import requests
from tqdm import tqdm

def _download_single(url, target_dir, prefix, headers, session):
    filename = f"{prefix}_{os.path.basename(url)}.html"
    file_path = os.path.join(target_dir, filename)
    
    if os.path.exists(file_path):
        return "skipped"
        
    full_url = f"https://urbansportsclub.com{url}"
    try:
        response = session.get(full_url, headers=headers, timeout=10)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            f.write(response.content)
        time.sleep(0.05) # Rate limiting gracefully, lowered since session is faster
        return "downloaded"
    except Exception as e:
        print(f"\nError downloading {url}: {e}")
        return "error"

def _download_list(urls, target_dir, prefix):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    print(f"Downloading {len(urls)} {prefix}s to {target_dir}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    downloaded_count = 0
    skipped_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        with requests.Session() as session:
            future_to_url = {executor.submit(_download_single, url, target_dir, prefix, headers, session): url for url in urls}
            with tqdm(total=len(urls), desc=f"Downloading {prefix}s") as pbar:
                for future in concurrent.futures.as_completed(future_to_url):
                    try:
                        res = future.result()
                        if res == "skipped":
                            skipped_count += 1
                        elif res == "downloaded":
                            downloaded_count += 1
                    except Exception as e:
                        print(f"\nError in download: {e}")
                    pbar.update(1)
def download_pages(venues, classes, temp_dir):
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    venues_dir = os.path.join(temp_dir, "venues")
    classes_dir = os.path.join(temp_dir, "classes")
    
    _download_list(venues, venues_dir, "venue")
    if classes:
        _download_list(classes, classes_dir, "class")

