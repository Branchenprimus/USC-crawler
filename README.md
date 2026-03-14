# USC Venue Scraper

We all hate the USC filter, so I created this project to scrape the USC website and extract all venues. 

## Features

- **Automated Discovery**: Crawls the USC API to intelligently map Target Cities and parse all associated Venues.
- **14-Day Scheduling**: For all discovered venues, retrieves their complete scheduled Course/Class offerings across the upcoming 14 days.
- **Bulk Downloading**: Concurrently bulk downloads both Venue and Class HTML datasets securely with rate limiting.
- **RAG-Optimized Denormalized Output**: Parses HTML to comprehensively join robust Venue data directly with each individual Class row via intelligent fuzzy-string matching (`difflib`). Returns a rich, single `data.csv` table optimized directly for RAG similarity search indexing.

## Structure

- `main.py`: Entry point for the scraper pipeline.
- `modules/`: Contains the core logic components.
  - `crawler.py`: Handles API interaction, discovering URLs for Venues and their 14-day Class schedules using Multithreading.
  - `downloader.py`: Manages accelerated concurrent HTML downloads.
  - `extractor.py`: Parses HTML via Regex, aligns Class locations with downloaded Venues securely, and dynamically outputs the dense, unified `data.csv`.
- `output/`: Directory where the final resulting `data.csv` is populated.

## Usage

Run the main script:

```bash
python3 main.py
```

### Options

| Flag | Description | Example |
|------|-------------|---------|
| `--city` | Target a built-in supported city explicitly to crawl (e.g. Köln, Berlin, München, Hamburg, Frankfurt). | `--city Köln` |
| `--test` | Run in test mode. Outputs to `test/data.csv`. Limits the crawl explicitly to exactly 5 venues, avoiding long wait-times, while retrieving the complete schedule for those 5 venues. | `--test` |
| `--limit` | Set a maximum number of venues to process. Useful for testing or partial scrapes. | `--limit 10` |
| `--url` | Provide a custom USC search URL to target specific cities or filters entirely overriding built-in default flags. | `--url "https://urbansportsclub.com/de/venues?city_id=1..."` |

**Example: Scrape all Venues and 14-Day Classes in Köln in Test Mode**
```bash
python3 main.py --city Köln --test
```

The script will:
1. Crawl the API to find the target city venues (max 5 due to `--test`).
2. Discover all Class URLs happening within the next 14 days for those specific Venues.
3. Rapidly multithread download all HTML instances to a temporary folder.
4. Extract structural information and map the Classes precisely to their Venues.
5. Create a flattened `test/data.csv` table optimized for AI.
6. Clean up the temporary files automatically.

## Requirements

- Python 3+
- Standard libraries only (`urllib`, `json`, `re`, `csv`, `os`, `glob`, `shutil`).

## n8n RAG Template

The project includes an [n8n workflow template](https://n8n.io/workflows/5010-rag-starter-template-using-simple-vector-stores-form-trigger-and-openai/) (`n8n/RAG-template.json`) to help you analyze the extracted data using AI.

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
