import os
import csv
import json
import argparse
from typing import List, Any
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    print("Error: The 'openai' library is not installed. Please run 'pip install -r requirements.txt'")
    exit(1)

def chunk_list(lst: List[Any], n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_embeddings(texts: List[str], client: OpenAI, model: str = "text-embedding-3-small") -> List[List[float]]:
    """Fetch embeddings from OpenAI API for a batch of texts."""
    response = client.embeddings.create(input=texts, model=model)
    return [data.embedding for data in response.data]

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for USC crawler data utilizing OpenAI.")
    parser.add_argument("input", nargs="?", default="output/data.csv", help="Input CSV file path (e.g. output/data.csv)")
    parser.add_argument("output", nargs="?", default="output/embeddings.json", help="Output JSON file path")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of rows to process per OpenAI API request")
    args = parser.parse_args()

    # Load from .env file
    load_dotenv()
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not found. Please set it in a .env file.")
        exit(1)

    client = OpenAI(api_key=api_key)

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found. Please run main.py first to generate the data.")
        exit(1)

    print(f"Reading dataset from {args.input}...")
    records = []
    with open(args.input, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    if not records:
        print("No data found to process within the CSV file.")
        return

    print(f"Found {len(records)} records. Generating embeddings in batches of {args.batch_size}...")
    
    # Process text in batches to avoid rate limits and reduce overhead
    for idx, batch in enumerate(chunk_list(records, args.batch_size)):
        print(f"Processing batch {idx + 1}...")
        texts_to_embed = [row.get("Combined_Text", "") for row in batch]
        
        try:
            embeddings = get_embeddings(texts_to_embed, client)
            for i, row in enumerate(batch):
                row["embedding"] = embeddings[i]
        except Exception as e:
            print(f"Error generating embeddings for batch {idx + 1}: {e}")
            exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    print(f"Saving final dataset with embeddings to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        
    print(f"Done! {len(records)} records processed effectively.")

if __name__ == "__main__":
    main()
