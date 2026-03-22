import urllib.request
import urllib.parse
import json
import re
import time
import sys
import concurrent.futures

CLASS_DISCOVERY_WORKERS = 15

def fetch_page(page_num, base_params=None):
    base_url = "https://urbansportsclub.com/de/venues"
    if base_params is None:
        # Default to Cologne if no params provided
        base_params = {
            "city_id": "9",
            "plan_type": "2",
            "type[]": "onsite"
        }
    
    # Create a copy to avoid modifying the original dictionary across iterations
    params = base_params.copy()
    params["page"] = str(page_num)

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

def parse_url_params(url):
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    # parse_qs returns lists for all values. We need to flatten them for single values,
    # but keep lists for array parameters like type[] or district[]
    # urllib.parse.urlencode with doseq=True expects lists for repeated params.
    
    clean_params = {}
    for key, value in query_params.items():
        if len(value) == 1 and not key.endswith('[]'):
             clean_params[key] = value[0]
        else:
             clean_params[key] = value
             
    return clean_params

from datetime import datetime, timedelta

def get_next_days(days=14):
    today = datetime.now()
    return [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

def fetch_venue_classes(venue_url, days=14):
    dates = get_next_days(days)
    class_urls = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    }
    import requests
    
    with requests.Session() as session:
        for date in dates:
            url = f"https://urbansportsclub.com{venue_url}?date={date}"
            try:
                response = session.get(url, headers=headers, timeout=10)
                html = response.text
                matches = re.findall(r'data-href="(/de/class-details/[^"]+)"', html)
                for class_url in matches:
                    class_urls.add(class_url)
            except Exception as e:
                pass # Silently skip errors on individual dates to avoid spam

    return list(class_urls)

def discover_urls(search_url=None, limit=None, days=14):
    base_params = None
    if search_url:
        print(f"Parsing parameters from: {search_url}")
        base_params = parse_url_params(search_url)
        # Remove page parameter if present in the input URL, as we iterate it manually
        if "page" in base_params:
            del base_params["page"]
            
    print("Starting URL discovery...")
    page = 1
    all_venues = set()
    
    while True:
        data = fetch_page(page, base_params)
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
            all_venues.add(url)
            if limit and len(all_venues) >= limit:
                break
        
        if limit and len(all_venues) >= limit:
            print(f"\nVenue limit of {limit} reached.")
            break
            
        if not show_more:
            break
            
        page += 1
        time.sleep(0.5)

    sorted_venues = sorted(list(all_venues))
    if limit:
        sorted_venues = sorted_venues[:limit]
        
    print(f"\nVenue discovery complete. Found {len(sorted_venues)} unique venues.")
    
    print(f"\nStarting class discovery for venues (next {days} days) using {CLASS_DISCOVERY_WORKERS} parallel workers...")
    all_classes = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CLASS_DISCOVERY_WORKERS) as executor:
        future_to_venue = {executor.submit(fetch_venue_classes, venue, days): venue for venue in sorted_venues}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_venue)):
            print(f"[{i+1}/{len(sorted_venues)}] Processing venue classes...", end="\r")
            try:
                classes = future.result()
                for c in classes:
                    all_classes.add(c)
            except Exception:
                pass
        
    sorted_classes = sorted(list(all_classes))
    print(f"\nClass discovery complete. Found {len(sorted_classes)} unique classes.")
    
    return sorted_venues, sorted_classes
