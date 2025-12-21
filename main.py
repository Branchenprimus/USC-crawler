import os
import shutil
import glob
from modules import crawler, downloader, extractor

def main():
    # Configuration
    TEMP_DIR = "temp"
    OUTPUT_FILE = os.path.join("output", "venues.csv")
    
    print("=== USC Venue Scraper ===")
    
    # Step 1: Discover URLs
    urls = crawler.discover_urls()
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
