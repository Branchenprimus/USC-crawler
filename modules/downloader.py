import os
import time
import urllib.request
import sys

def download_venues(urls, temp_dir):
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    print(f"Downloading {len(urls)} venues to {temp_dir}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    downloaded_count = 0
    skipped_count = 0
    
    for i, url in enumerate(urls):
        filename = f"venue_{os.path.basename(url)}.html"
        file_path = os.path.join(temp_dir, filename)
        
        if os.path.exists(file_path):
            skipped_count += 1
            continue
            
        full_url = f"https://urbansportsclub.com{url}"
        print(f"[{i+1}/{len(urls)}] Fetching {url}...", end="\r")
        
        req = urllib.request.Request(full_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
            downloaded_count += 1
            time.sleep(0.2) # Rate limiting
        except Exception as e:
            print(f"\nError downloading {url}: {e}")
            
    print(f"\nDownload complete. New: {downloaded_count}, Skipped: {skipped_count}")
