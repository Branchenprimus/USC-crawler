import urllib.request
import urllib.parse
import json
import re
import time
import sys

def fetch_page(page_num):
    base_url = "https://urbansportsclub.com/de/venues"
    params = {
        "city_id": "9",
        "plan_type": "2",
        "type[]": "onsite",
        "page": str(page_num)
    }
    query_string = urllib.parse.urlencode(params, doseq=True)
    url = f"{base_url}?{query_string}"
    print(f"Fetching page {page_num} from API...", end="\r")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"\nFailed to fetch page {page_num}: Status {response.status}")
                return None
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"\nError fetching page {page_num}: {e}")
        return None

def extract_urls_from_html(html_content):
    pattern = r'href="(/de/venues/[^"]*)"'
    return re.findall(pattern, html_content)

def discover_urls():
    print("Starting URL discovery...")
    page = 1
    all_urls = set()
    
    while True:
        data = fetch_page(page)
        if not data:
            break
            
        success = data.get("success", False)
        if not success:
            print("\nAPI returned success=false. Stopping.")
            break
            
        content = data.get("data", {}).get("content", "")
        show_more = data.get("data", {}).get("showMore", False)
        
        urls = extract_urls_from_html(content)
        
        for url in urls:
            all_urls.add(url)
            
        if not show_more:
            break
            
        page += 1
        time.sleep(0.5)

    print(f"\nDiscovery complete. Found {len(all_urls)} unique URLs.")
    return sorted(list(all_urls))
