import shutil
import argparse
import time
from modules import crawler, downloader, extractor, datasets

def main():
    parser = argparse.ArgumentParser(description="Scrape Urban Sports Club venues.")
    parser.add_argument("--url", help="Full USC search URL (e.g., https://urbansportsclub.com/de/venues?city_id=1...) to override default search filters.")
    parser.add_argument("--city", type=str, help="Name of the city to scrape (e.g., Köln, Berlin, München, Hamburg, Frankfurt).")
    parser.add_argument("--contract", type=str, default="m", help="Contract tier to crawl: s, m, l, xl. Default=m.")
    parser.add_argument("--limit", type=int, help="Max number of venues to process.")
    parser.add_argument("--days", type=int, default=14, help="Number of days to search for classes ahead. Default=14.")
    args = parser.parse_args()

    # Configuration
    TEMP_DIR = "temp"
    
    start_time = time.time()
    print("=== USC Venue & Class Scraper ===")
        
    CITY_MAPPING = {
        "berlin": 1,
        "münchen": 2,
        "munich": 2,
        "hamburg": 3,
        "frankfurt": 4,
        "stuttgart": 5,
        "köln": 9,
        "cologne": 9,
        "düsseldorf": 10,
        "leipzig": 11,
        "hannover": 13,
        "nürnberg": 14,
        "bonn": 16,
        "bremen": 18
    }
    contract = (args.contract or "m").lower()
    if contract not in crawler.CONTRACT_PLAN_TYPES:
        supported_contracts = ", ".join(key.upper() for key in crawler.CONTRACT_PLAN_TYPES)
        raise SystemExit(f"Unsupported contract '{args.contract}'. Choose one of: {supported_contracts}")
    
    city_id_to_name = {
        1: "Berlin",
        2: "München",
        3: "Hamburg",
        4: "Frankfurt",
        5: "Stuttgart",
        9: "Köln",
        10: "Düsseldorf",
        11: "Leipzig",
        13: "Hannover",
        14: "Nürnberg",
        16: "Bonn",
        18: "Bremen",
    }

    if args.city and not args.url:
        city_name = args.city.lower()
        if city_name in CITY_MAPPING:
            city_id = CITY_MAPPING[city_name]
            args.url = crawler.build_search_url(city_id, contract)
            print(f"Targeting city: {args.city} (ID: {city_id}) · Contract: {contract.upper()}")
        else:
            print(f"Warning: City '{args.city}' not found in known mapping. Supported cities include: {', '.join(CITY_MAPPING.keys())}")

    target_city = args.city
    if not target_city and args.url:
        url_params = crawler.parse_url_params(args.url)
        try:
            city_id = int(url_params.get("city_id"))
        except (TypeError, ValueError):
            city_id = None
        target_city = city_id_to_name.get(city_id, "custom")
        plan_type = str(url_params.get("plan_type", "")).strip()
        for contract_name, contract_plan_type in crawler.CONTRACT_PLAN_TYPES.items():
            if str(contract_plan_type) == plan_type:
                contract = contract_name
                break

    if not target_city:
        target_city = "custom"

    output_config = datasets.get_dataset_config(target_city, False, contract)
    OUTPUT_DIR = output_config["dataset_dir"]
    print(f"Writing dataset to: {OUTPUT_DIR}")
    
    # Step 1: Discover URLs
    venues, classes = crawler.discover_urls(search_url=args.url, limit=args.limit, days=args.days)
    if not venues:
        print("No venues found. Exiting.")
        return

    # Step 2: Download HTML files
    downloader.download_pages(venues, classes, TEMP_DIR)
    
    # Step 3: Extract content to unified CSV
    extractor.process_directory(TEMP_DIR, OUTPUT_DIR)
    
    # Step 5: Cleanup
    print("\nCleaning up temporary files...")
    # The user requested to "delete the html files", "if needed create a temp folder".
    # So we should delete the contents of temp folder after processing.
    try:
        shutil.rmtree(TEMP_DIR)
        print(f"Removed temporary directory: {TEMP_DIR}")
    except Exception as e:
        print(f"Error removing {TEMP_DIR}: {e}")
        
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    print(f"\n=== Done in {minutes}m {seconds}s ===")

if __name__ == "__main__":
    main()
