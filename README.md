# USC Venue Scraper

We all hate the USC filter, so I created this project to scrape the USC website and extract all venues. 

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

## n8n RAG Template

The project includes an n8n workflow template (`n8n/RAG-template.json`) to help you analyze the extracted data using AI.

### Features
This RAG (Retrieval Augmented Generation) workflow allows you to:
1.  **Load Data**: Upload the generated `venues.csv` (or PDFs) to an in-memory vector store.
2.  **Chat**: Interactively query your data using a chat interface powered by OpenAI (GPT-4o-mini).

### Work Modes
You can run n8n in two primary ways:

-   **Local Hosting (Self-Hosted)**:
    -   Run n8n on your own machine using `npm` or `docker`.
    -   Best for privacy, free usage, and local development.
    -   Command: `npx n8n` (requires Node.js).

-   **Cloud Hosting (SaaS)**:
    -   Use the managed n8n.io service.
    -   Easiest to set up, secure, and accessible from anywhere.
    -   Requires a subscription but handles maintenance for you.

To use the template, simply import the `.json` file into your n8n workflows dashboard.
