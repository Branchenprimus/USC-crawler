import os
import shutil
import glob
import argparse
from modules import crawler, downloader, extractor

def main():
    parser = argparse.ArgumentParser(description="Scrape Urban Sports Club venues.")
    parser.add_argument("--url", help="Full USC search URL (e.g., https://urbansportsclub.com/de/venues?city_id=1...) to override default search filters.")
    parser.add_argument("--test", action="store_true", help="Run in test mode (limit venues, output to test folder).")
    parser.add_argument("--limit", type=int, help="Max number of venues to process. Defaults to 5 in test mode.")
    args = parser.parse_args()

    # Configuration
    TEMP_DIR = "temp"
    if args.test:
        OUTPUT_DIR = "test"
        if args.limit is None:
            args.limit = 5
    else:
        OUTPUT_DIR = "output"
        
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "venues.csv")
    
    print("=== USC Venue Scraper ===")
    if args.test:
        print("TEST MODE ENABLED")
    
    # Step 1: Discover URLs
    urls = crawler.discover_urls(search_url=args.url, limit=args.limit)
    if not urls:
        print("No URLs found. Exiting.")
        return

    # Step 2: Download HTML files
    downloader.download_venues(urls, TEMP_DIR)
    
    # Step 3: Extract content to CSV
    extractor.process_directory(TEMP_DIR, OUTPUT_FILE)
    
    # Step 4: Cleanup
    print("\nCleaning up temporary files...")
    # The user requested to "delete the html files", "if needed create a temp folder".
    # So we should delete the contents of temp folder after processing.
    try:
        shutil.rmtree(TEMP_DIR)
        print(f"Removed temporary directory: {TEMP_DIR}")
    except Exception as e:
        print(f"Error removing {TEMP_DIR}: {e}")
        
    print("\n=== Done ===")

if __name__ == "__main__":
    main()
