import os
import csv
import json
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Any, Tuple
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


def process_batch(
    batch_index: int,
    batch: List[dict],
    client: OpenAI,
    model: str,
    max_retries: int,
) -> Tuple[int, List[dict]]:
    texts_to_embed = [row.get("Combined_Text", "") for row in batch]
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            embeddings = get_embeddings(texts_to_embed, client, model=model)
            for i, row in enumerate(batch):
                row["embedding"] = embeddings[i]
            return batch_index, batch
        except Exception as e:
            last_error = e
            is_rate_limit = "rate_limit" in str(e).lower()
            if attempt >= max_retries:
                break

            wait_seconds = min(120, 5 * (2 ** attempt)) if is_rate_limit else min(30, 2 * (attempt + 1))
            print(
                f"Retrying batch {batch_index + 1} after error: {e}. "
                f"Attempt {attempt + 1}/{max_retries}, waiting {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    raise RuntimeError(f"Batch {batch_index + 1} failed after {max_retries + 1} attempts: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for USC crawler data utilizing OpenAI.")
    parser.add_argument("input", nargs="?", default="output/data.csv", help="Input CSV file path (e.g. output/data.csv)")
    parser.add_argument("output", nargs="?", default="output/embeddings.json", help="Output JSON file path")
    parser.add_argument("--batch-size", type=int, default=200, help="Number of rows to process per OpenAI API request")
    parser.add_argument("--concurrency", type=int, default=3, help="Number of embedding requests to run in parallel")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model to use")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per batch on transient errors")
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

    batches = list(chunk_list(records, args.batch_size))
    total_batches = len(batches)
    print(
        f"Found {len(records)} records. Generating embeddings in {total_batches} batches "
        f"of {args.batch_size} with concurrency {args.concurrency}..."
    )

    processed_batches = [None] * total_batches
    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {
            executor.submit(
                process_batch,
                idx,
                batch,
                client,
                args.model,
                args.max_retries,
            ): idx
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(futures):
            idx = futures[future]
            print(f"Processing batch {idx + 1}/{total_batches}...")
            try:
                batch_index, processed_batch = future.result()
                processed_batches[batch_index] = processed_batch
                completed += 1
                print(f"Completed batch {completed}/{total_batches}")
            except Exception as e:
                print(f"Error generating embeddings for batch {idx + 1}: {e}")
                executor.shutdown(wait=False, cancel_futures=True)
                exit(1)

    records = [row for batch in processed_batches if batch for row in batch]

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    print(f"Saving final dataset with embeddings to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        
    print(f"Done! {len(records)} records processed effectively.")

if __name__ == "__main__":
    main()
