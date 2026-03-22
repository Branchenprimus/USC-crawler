import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP

try:
    import tiktoken
except ImportError:
    print("Error: The 'tiktoken' library is not installed. Please run 'pip install -r requirements.txt'")
    raise SystemExit(1)


MODEL_PRICING_PER_MILLION = {
    "text-embedding-3-small": Decimal("0.02"),
    "text-embedding-3-large": Decimal("0.13"),
}

BATCH_DISCOUNT = Decimal("0.5")


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def main():
    parser = argparse.ArgumentParser(
        description="Estimate OpenAI embedding cost for a USC crawler CSV."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="output/data.csv",
        help="Input CSV file path (default: output/data.csv)",
    )
    parser.add_argument(
        "--column",
        default="Combined_Text",
        help="CSV column to tokenize (default: Combined_Text)",
    )
    parser.add_argument(
        "--model",
        choices=sorted(MODEL_PRICING_PER_MILLION),
        default="text-embedding-3-small",
        help="Embedding model to estimate (default: text-embedding-3-small)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Estimate Batch API pricing instead of standard pricing",
    )
    args = parser.parse_args()

    encoding = tiktoken.get_encoding("cl100k_base")

    rows = 0
    total_chars = 0
    total_tokens = 0
    max_tokens = 0

    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if args.column not in (reader.fieldnames or []):
            print(
                f"Error: Column '{args.column}' not found. "
                f"Available columns: {', '.join(reader.fieldnames or [])}"
            )
            raise SystemExit(1)

        for row in reader:
            text = row.get(args.column) or ""
            token_count = len(encoding.encode(text))
            rows += 1
            total_chars += len(text)
            total_tokens += token_count
            max_tokens = max(max_tokens, token_count)

    if rows == 0:
        print("No rows found in the input CSV.")
        return

    price_per_million = MODEL_PRICING_PER_MILLION[args.model]
    if args.batch:
        price_per_million *= BATCH_DISCOUNT

    total_cost = (Decimal(total_tokens) / Decimal("1000000")) * price_per_million

    print(f"Input file: {args.input}")
    print(f"Column: {args.column}")
    print(f"Model: {args.model}")
    print(f"Mode: {'Batch API' if args.batch else 'Standard API'}")
    print(f"Rows: {rows}")
    print(f"Total chars: {total_chars}")
    print(f"Total tokens: {total_tokens}")
    print(f"Avg tokens/row: {total_tokens / rows:.2f}")
    print(f"Max tokens/row: {max_tokens}")
    print(f"Price per 1M tokens: ${money(price_per_million)}")
    print(f"Estimated total cost: ${money(total_cost)}")
    print("Pricing reference date: 2026-03-14")


if __name__ == "__main__":
    main()
