# USC Venue Scraper

This project automates the process of discovering and extracting venue information from Urban Sports Club.

## Features

- **Automated Discovery**: Crawls the USC API to discover available venues associated with specific city and plan types.
- **Bulk Downloading**: Downloads venue HTML pages efficiently.
- **Data Extraction**: Parses HTML content to extract structrued data including names, ratings, disciplines, descriptions, and addresses.
- **CSV Export**: Outputs the data into a clean, quoted CSV file.

## Structure

- `main.py`: Entry point for the scraper.
- `modules/`: Contains the core logic components.
  - `crawler.py`: Handles API interaction and URL discovery.
  - `downloader.py`: Manages file downloads.
  - `extractor.py`: Parses HTML and writes CSV.
- `output/`: Directory where the final `venues.csv` is saved.

## Usage

Run the main script:

```bash
python3 main.py
```

The script will:
1. Crawl the API to find all venues.
2. Download them to a temporary folder.
3. Extract information to `output/venues.csv`.
4. Clean up the temporary files automatically.

## Requirements

- Python 3+
- Standard libraries only (`urllib`, `json`, `re`, `csv`, `os`, `glob`, `shutil`).
