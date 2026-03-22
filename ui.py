import json
import os
import html
import re
import subprocess
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
import tiktoken
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from modules import crawler, datasets

load_dotenv()

st.set_page_config(page_title="USC Venue Explorer", page_icon="USC", layout="wide")

ENV_PATH = ".env"
CITY_OPTIONS = [
    "Köln",
    "Berlin",
    "München",
    "Hamburg",
    "Frankfurt",
    "Stuttgart",
    "Düsseldorf",
    "Leipzig",
    "Hannover",
    "Nürnberg",
    "Bonn",
    "Bremen",
]
CITY_IDS = {
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
    "bremen": 18,
}
MODEL_PRICING_PER_MILLION = {
    "text-embedding-3-small": Decimal("0.02"),
    "text-embedding-3-large": Decimal("0.13"),
}
CHAT_MODEL = "gpt-4o"
UI_STATE_VERSION = "venue-tiles-v1"


st.title("USC Venue Explorer")
st.caption("Choose a city first, then inspect the dataset or start a fresh crawl.")
st.markdown(
    """
    <style>
    .result-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 16px;
        margin-top: 14px;
    }
    .venue-tile {
        background: linear-gradient(180deg, rgba(250,252,255,0.96), rgba(243,246,255,0.94));
        border: 1px solid rgba(103, 132, 255, 0.16);
        border-radius: 24px;
        padding: 18px 18px 16px;
        box-shadow: 0 18px 40px rgba(46, 70, 140, 0.10);
    }
    .venue-top {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    .venue-eyebrow {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #6f7bc9;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .venue-title {
        font-size: 1.18rem;
        line-height: 1.25;
        color: #17203d;
        font-weight: 800;
        margin: 0;
    }
    .venue-meta {
        color: #52607f;
        font-size: 0.92rem;
        margin-top: 8px;
    }
    .venue-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        background: linear-gradient(135deg, #4e8dff, #6f6cff);
        color: white !important;
        text-decoration: none !important;
        border-radius: 999px;
        padding: 10px 14px;
        font-size: 0.88rem;
        font-weight: 700;
        box-shadow: 0 10px 24px rgba(80, 108, 255, 0.22);
    }
    .class-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-top: 14px;
    }
    .class-card {
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(133, 149, 232, 0.16);
        border-radius: 18px;
        padding: 13px 14px;
    }
    .class-title {
        color: #1e2850;
        font-size: 1rem;
        font-weight: 700;
        margin: 0 0 6px 0;
    }
    .class-meta {
        color: #5e6a88;
        font-size: 0.88rem;
        margin-bottom: 6px;
    }
    .class-description {
        color: #36415d;
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .summary-card {
        background: linear-gradient(135deg, rgba(235,244,255,0.88), rgba(243,239,255,0.9));
        border: 1px solid rgba(118, 137, 255, 0.18);
        border-radius: 20px;
        padding: 14px 16px;
        margin: 10px 0 16px;
        color: #1f2a4f;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 18px;
        margin: 18px 0 12px;
    }
    .info-card {
        position: relative;
        overflow: hidden;
        background: radial-gradient(circle at top left, rgba(255,255,255,0.98), rgba(239,244,255,0.92));
        border: 1px solid rgba(112, 134, 255, 0.18);
        border-radius: 22px;
        padding: 18px 20px;
        box-shadow: 0 16px 36px rgba(46, 70, 140, 0.10);
    }
    .info-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #4e8dff, #7a6cff);
        opacity: 0.7;
    }
    .info-card h4 {
        margin: 6px 0 14px 0;
        color: #1c2550;
        font-size: 1.05rem;
        font-weight: 800;
    }
    .info-list {
        display: grid;
        gap: 12px;
    }
    .info-row {
        display: grid;
        grid-template-columns: minmax(120px, 150px) 1fr;
        gap: 10px;
        align-items: center;
        border-bottom: 1px solid rgba(112, 134, 255, 0.10);
        padding-bottom: 10px;
    }
    .info-row:last-child {
        border-bottom: 0;
        padding-bottom: 0;
    }
    .info-label {
        color: #607099;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 800;
    }
    .info-value {
        color: #1d274f;
        font-size: 0.96rem;
        font-weight: 600;
        text-align: right;
        word-break: break-word;
        font-family: "IBM Plex Mono", "SFMono-Regular", "Consolas", "Liberation Mono", "Menlo", monospace;
        background: rgba(78, 141, 255, 0.08);
        padding: 4px 8px;
        border-radius: 10px;
    }
    @media (max-width: 720px) {
        .info-row {
            grid-template-columns: 1fr;
            align-items: start;
        }
        .info-value {
            text-align: left;
            justify-self: start;
        }
    }
    .action-shell {
        background: linear-gradient(135deg, rgba(236,244,255,0.92), rgba(244,239,255,0.92));
        border: 1px solid rgba(114, 134, 255, 0.16);
        border-radius: 22px;
        padding: 16px 18px;
        margin-top: 8px;
    }
    .action-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
    }
    .action-eyebrow {
        color: #6d78c8;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
    }
    .action-title {
        color: #1d2750;
        font-size: 1.02rem;
        font-weight: 800;
        margin-top: 4px;
    }
    .pill-ok, .pill-missing {
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 0.84rem;
        font-weight: 800;
        white-space: nowrap;
    }
    .pill-ok {
        background: rgba(42, 176, 116, 0.12);
        color: #1e8e60;
    }
    .pill-missing {
        background: rgba(255, 176, 74, 0.16);
        color: #a76100;
    }
    .action-caption {
        color: #55617f;
        font-size: 0.92rem;
        margin-top: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def infer_dataset_city(df):
    if "Venue Address" not in df.columns:
        return None

    addresses = df["Venue Address"].dropna().astype(str)
    cities = []
    for address in addresses:
        parts = [part.strip() for part in address.split(",") if part.strip()]
        if not parts:
            continue
        last_part = parts[-1]
        city = last_part.split()[-1] if last_part.split() else None
        if city and city != "N/A":
            cities.append(city)

    if not cities:
        return None

    return pd.Series(cities).mode().iat[0]


def load_openai_api_key():
    return os.getenv("OPENAI_API_KEY", "").strip()


def mask_api_key(api_key):
    if not api_key:
        return "Not configured"
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


def save_openai_api_key(api_key):
    with open(ENV_PATH, "w", encoding="utf-8") as env_file:
        env_file.write(f"OPENAI_API_KEY={api_key.strip()}\n")

    os.environ["OPENAI_API_KEY"] = api_key.strip()
    load_rag_chain.clear()


def bytes_to_human(size):
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def money(value):
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def make_city_url(city):
    city_id = CITY_IDS[city.lower()]
    return f"https://urbansportsclub.com/de/venues?city_id={city_id}&plan_type=2&type%5B%5D=onsite"


def get_summary_cache_path(data_path):
    data_file = Path(data_path)
    return data_file.with_name(f".{data_file.stem}.summary.json")


def load_summary_cache(data_path, embeddings_path):
    cache_path = get_summary_cache_path(data_path)
    if not cache_path.exists():
        return None

    try:
        with cache_path.open("r", encoding="utf-8") as f:
            cached = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    data_file = Path(data_path)
    embeddings_file = Path(embeddings_path)
    expected = {
        "data_mtime": data_file.stat().st_mtime if data_file.exists() else None,
        "embeddings_mtime": embeddings_file.stat().st_mtime if embeddings_file.exists() else None,
    }
    if (
        cached.get("data_mtime") != expected["data_mtime"]
        or cached.get("embeddings_mtime") != expected["embeddings_mtime"]
    ):
        return None

    return cached.get("summary")


def save_summary_cache(data_path, embeddings_path, summary):
    cache_path = get_summary_cache_path(data_path)
    data_file = Path(data_path)
    embeddings_file = Path(embeddings_path)
    payload = {
        "data_mtime": data_file.stat().st_mtime if data_file.exists() else None,
        "embeddings_mtime": embeddings_file.stat().st_mtime if embeddings_file.exists() else None,
        "summary": summary,
    }
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


@st.cache_data(show_spinner=False)
def load_dataset_summary(data_path, embeddings_path):
    path = Path(data_path)
    if not path.exists():
        return None

    cached_summary = load_summary_cache(data_path, embeddings_path)
    if cached_summary:
        return cached_summary

    df = pd.read_csv(path)
    summary = {
        "city": infer_dataset_city(df),
        "classes": len(df),
        "venues": df["Venue Name"].nunique() if "Venue Name" in df.columns else 0,
        "categories": df["Class Category"].nunique() if "Class Category" in df.columns else 0,
        "data_size": bytes_to_human(path.stat().st_size),
        "data_updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime)),
        "token_count": 0,
        "embedding_rows": 0,
        "embedding_dims": None,
        "embedding_size": None,
        "embedding_updated": None,
    }

    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = 0
    for text in df.get("Combined_Text", pd.Series(dtype=str)).fillna("").astype(str):
        token_count += len(encoding.encode(text))
    summary["token_count"] = token_count

    embeddings = Path(embeddings_path)
    if embeddings.exists():
        with embeddings.open("r", encoding="utf-8") as f:
            records = json.load(f)
        first_embedding = next(
            (
                record.get("embedding")
                for record in records
                if isinstance(record.get("embedding"), list) and record.get("embedding")
            ),
            None,
        )
        summary["embedding_rows"] = len(records)
        summary["embedding_dims"] = len(first_embedding) if first_embedding else None
        summary["embedding_size"] = bytes_to_human(embeddings.stat().st_size)
        summary["embedding_updated"] = time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(embeddings.stat().st_mtime)
        )

    save_summary_cache(data_path, embeddings_path, summary)
    return summary


@st.cache_data(show_spinner=False, ttl=1800)
def count_city_venues(city):
    search_url = make_city_url(city)
    base_params = crawler.parse_url_params(search_url)
    if "page" in base_params:
        del base_params["page"]

    page = 1
    venues = set()
    while True:
        data = crawler.fetch_page(page, base_params)
        if not data or not data.get("success", False):
            break

        content = data.get("data", {}).get("content", "")
        for url in crawler.extract_urls_from_html(content):
            venues.add(url)

        if not data.get("data", {}).get("showMore", False):
            break

        page += 1

    return len(venues)


def get_reference_summary(prefer_test_data):
    for mode in [prefer_test_data, not prefer_test_data]:
        for candidate in datasets.iter_dataset_configs(mode):
            summary = load_dataset_summary(candidate["data_path"], candidate["embeddings_path"])
            if summary:
                return summary
    return None


def estimate_embedding_cost_from_reference(venue_count, prefer_test_data, model="text-embedding-3-small"):
    reference = get_reference_summary(prefer_test_data)
    if not reference or reference["venues"] == 0:
        return None

    avg_tokens_per_venue = Decimal(reference["token_count"]) / Decimal(reference["venues"])
    estimated_tokens = Decimal(venue_count) * avg_tokens_per_venue
    total_cost = (estimated_tokens / Decimal("1000000")) * MODEL_PRICING_PER_MILLION[model]
    return {
        "estimated_tokens": int(estimated_tokens),
        "estimated_cost": money(total_cost),
        "reference_city": reference["city"] or "current dataset",
    }


def estimate_embedding_cost_from_tokens(token_count, model="text-embedding-3-small"):
    total_cost = (Decimal(token_count) / Decimal("1000000")) * MODEL_PRICING_PER_MILLION[model]
    return money(total_cost)


def find_dataset_for_city(selected_city, use_test_data):
    preferred = datasets.get_dataset_config(selected_city, use_test_data)
    preferred_summary = load_dataset_summary(
        preferred["data_path"],
        preferred["embeddings_path"],
    )
    if preferred_summary:
        preferred["summary"] = preferred_summary
        return preferred

    legacy = datasets.get_legacy_dataset_config(use_test_data)
    legacy_summary = load_dataset_summary(
        legacy["data_path"],
        legacy["embeddings_path"],
    )
    if (
        legacy_summary
        and legacy_summary.get("city")
        and legacy_summary["city"].lower() == selected_city.lower()
    ):
        legacy["summary"] = legacy_summary
        return legacy

    return preferred


def get_available_datasets():
    available = []
    for use_test_data in [False, True]:
        for config in datasets.iter_dataset_configs(use_test_data):
            summary = load_dataset_summary(config["data_path"], config["embeddings_path"])
            if summary:
                available.append(
                    {
                        **config,
                        "use_test_data": use_test_data,
                        "summary": summary,
                    }
                )
    return available


def choose_dataset(selected_city, prefer_test_data):
    dataset_config = find_dataset_for_city(selected_city, prefer_test_data)
    dataset_summary = dataset_config.get("summary") or load_dataset_summary(
        dataset_config["data_path"],
        dataset_config["embeddings_path"],
    )

    if not dataset_summary:
        return dataset_config, None, None

    if dataset_config.get("is_legacy"):
        return (
            dataset_config,
            dataset_summary,
            f"Using the legacy {dataset_config['label'].lower()} dataset for {selected_city}. A new crawl will store future runs in a city-specific folder.",
        )

    return dataset_config, dataset_summary, None


@st.cache_resource
def load_rag_chain(data_path, embeddings_path):
    if os.path.exists(embeddings_path):
        with open(embeddings_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        documents = []
        embeddings_list = []
        metadatas = []
        for record in records:
            combined_text = record.get("Combined_Text", "")
            embedding = record.get("embedding", [])
            if combined_text and embedding:
                documents.append(Document(page_content=combined_text, metadata={"source": record}))
                embeddings_list.append(embedding)
                metadatas.append({"source": record})

        embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.from_embeddings(
            text_embeddings=list(zip([doc.page_content for doc in documents], embeddings_list)),
            embedding=embedding_model,
            metadatas=metadatas,
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
        prompt = ChatPromptTemplate.from_template(
            """You are an assistant for answering questions about Urban Sports Club venues and classes.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Keep the answer concise and formatting clear. Structure schedules logically.
Context: {context}
Question: {input}
Answer:"""
        )
        return retriever, prompt, llm

    if not os.path.exists(data_path):
        return None

    df = pd.read_csv(data_path)
    if "Combined_Text" not in df.columns:
        return None

    documents = [Document(page_content=str(row), metadata={"source": idx}) for idx, row in df["Combined_Text"].items()]
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(documents, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_template(
        """You are an assistant for answering questions about Urban Sports Club venues and classes.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Keep the answer concise and formatting clear. Structure schedules logically.
Context: {context}
Question: {input}
Answer:"""
    )
    return retriever, prompt, llm


def answer_question(rag_components, user_input):
    retriever, prompt, llm = rag_components
    documents = retriever.invoke(user_input)
    context = "\n\n".join(doc.page_content for doc in documents)
    messages = prompt.invoke({"context": context, "input": user_input})
    response = llm.invoke(messages)
    return response.content, documents


def _clean_value(value, fallback="N/A"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _truncate_text(text, limit=180):
    text = _clean_value(text, "")
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1].rstrip()}..."


def build_result_groups(documents):
    grouped = {}
    for doc in documents:
        source = doc.metadata.get("source") if isinstance(doc.metadata, dict) else None
        if not isinstance(source, dict):
            continue

        venue_name = _clean_value(source.get("Venue Name"), "Unknown Venue")
        entry = grouped.setdefault(
            venue_name,
            {
                "venue_name": venue_name,
                "rating": _clean_value(source.get("Venue Rating")),
                "disciplines": _clean_value(source.get("Venue Disciplines")),
                "address": _clean_value(source.get("Venue Address")),
                "description": _clean_value(source.get("Venue Description"), ""),
                "usc_url": _clean_value(source.get("Venue USC URL"), ""),
                "classes": [],
            },
        )
        if not entry["usc_url"] or entry["usc_url"] == "N/A":
            entry["usc_url"] = _clean_value(source.get("Venue USC URL"), "")

        entry["classes"].append(
            {
                "title": _clean_value(source.get("Class Title")),
                "date": _clean_value(source.get("Class Date")),
                "category": _clean_value(source.get("Class Category")),
                "description": _truncate_text(source.get("Class Description"), 220),
            }
        )

    return sorted(grouped.values(), key=lambda item: (item["venue_name"].lower(), len(item["classes"])))


def render_result_groups(answer_text, grouped_results):
    if not grouped_results:
        return

    for venue in grouped_results:
        card = st.container(border=True)
        header = card.columns([3, 1])
        with header[0]:
            card.caption("Venue")
            card.subheader(venue["venue_name"])
            meta_bits = []
            if venue["rating"] != "N/A":
                meta_bits.append(f"Rating {venue['rating']}")
            address_value = venue.get("address")
            if address_value and address_value != "N/A":
                maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(address_value)}"
                meta_bits.append(f"[{address_value}]({maps_url})")
            if meta_bits:
                card.markdown(" · ".join(meta_bits))
            if venue["description"]:
                card.markdown(_truncate_text(venue["description"], 160))
        with header[1]:
            if venue.get("usc_url") and venue["usc_url"] != "N/A":
                card.link_button("Open on USC", venue["usc_url"])

        card.caption(f"{len(venue['classes'])} matching classes")
        for class_item in venue["classes"]:
            class_box = card.container()
            class_box.markdown(f"**{class_item['title']}**")
            meta_parts = [class_item["date"]]
            if class_item["category"] != "N/A":
                meta_parts.append(class_item["category"])
            class_box.caption(" · ".join(meta_parts))
            class_box.write(class_item["description"] or "No description available.")
def run_crawler(city, days, use_test_data):
    if os.path.exists("/.dockerenv"):
        python_exec = "python"
    else:
        python_exec = ".venv/bin/python" if os.path.exists(".venv/bin/python") else "python3"

    cmd = [python_exec, "-u", "main.py", "--city", city, "--days", str(days)]
    if use_test_data:
        cmd.append("--test")
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def run_crawler_with_progress(city, days, use_test_data):
    if os.path.exists("/.dockerenv"):
        python_exec = "python"
    else:
        python_exec = ".venv/bin/python" if os.path.exists(".venv/bin/python") else "python3"

    cmd = [python_exec, "-u", "main.py", "--city", city, "--days", str(days)]
    if use_test_data:
        cmd.append("--test")

    progress_bar = st.progress(0, text=f"Preparing crawl for {city}...")
    status = st.empty()
    log_block = st.empty()
    logs = []

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    for raw_line in iter(process.stdout.readline, ""):
        line = raw_line.strip()
        if not line:
            continue

        logs.append(line)
        log_block.code("\n".join(logs[-25:]))

        if "=== USC Venue & Class Scraper ===" in line:
            progress_bar.progress(0.03, text=f"Starting crawl for {city}...")
            continue
        if "Targeting city:" in line:
            status.info(line)
            progress_bar.progress(0.07, text=f"Targeting {city}...")
            continue
        if "Starting URL discovery" in line:
            progress_bar.progress(0.12, text=f"Discovering venues for {city}...")
            continue

        class_worker_match = re.search(
            r"Starting class discovery.*using (\d+) parallel workers",
            line,
            re.IGNORECASE,
        )
        if class_worker_match:
            workers = int(class_worker_match.group(1))
            status.info(f"Class discovery is running with {workers} parallel workers.")
            progress_bar.progress(0.27, text=f"Discovering classes for {city} with {workers} workers...")
            continue

        venue_match = re.search(r"Venue discovery complete\. Found (\d+) unique venues\.", line)
        if venue_match:
            venue_count = int(venue_match.group(1))
            status.info(f"Discovered {venue_count} venues.")
            progress_bar.progress(0.25, text=f"Discovered {venue_count} venues for {city}.")
            continue

        class_progress = re.search(r"\[(\d+)/(\d+)\] Processing venue classes", line)
        if class_progress:
            current = int(class_progress.group(1))
            total = int(class_progress.group(2))
            progress = 0.25 + (current / total) * 0.25
            progress_bar.progress(
                min(progress, 0.5),
                text=f"Discovering classes for {city}: {current}/{total} venues checked",
            )
            continue

        class_match = re.search(r"Class discovery complete\. Found (\d+) unique classes\.", line)
        if class_match:
            class_count = int(class_match.group(1))
            status.info(f"Discovered {class_count} classes.")
            progress_bar.progress(0.52, text=f"Discovered {class_count} classes for {city}.")
            continue

        download_match = re.search(r"Downloading (\d+) (venue|class)s to", line)
        if download_match:
            count = int(download_match.group(1))
            kind = download_match.group(2)
            progress = 0.6 if kind == "venue" else 0.72
            progress_bar.progress(progress, text=f"Downloading {count} {kind}s for {city}...")
            continue

        download_worker_match = re.search(
            r"Using (\d+) parallel download workers for (venue|class)s",
            line,
            re.IGNORECASE,
        )
        if download_worker_match:
            workers = int(download_worker_match.group(1))
            kind = download_worker_match.group(2)
            status.info(f"{kind.title()} downloads are running with {workers} parallel workers.")
            continue

        if "Successfully wrote" in line and "joined class entries" in line:
            progress_bar.progress(0.9, text=f"Saving crawl results for {city}...")
            continue
        if "Cleaning up temporary files" in line:
            progress_bar.progress(0.96, text=f"Cleaning up crawl temp files for {city}...")
            continue
        if "=== Done in" in line:
            progress_bar.progress(1.0, text=f"Crawl finished for {city}.")
            status.success(line)
            continue

    return_code = process.wait()
    combined_output = "\n".join(logs)

    if return_code != 0:
        progress_bar.empty()
        status.empty()
        raise subprocess.CalledProcessError(return_code, cmd, output=combined_output)

    progress_bar.progress(1.0, text=f"Crawl finished for {city}.")
    status.success("Crawl completed successfully.")
    return combined_output


def run_embeddings(data_path, embeddings_path):
    if os.path.exists("/.dockerenv"):
        python_exec = "python"
    else:
        python_exec = ".venv/bin/python" if os.path.exists(".venv/bin/python") else "python3"

    cmd = [python_exec, "-u", "embed.py", data_path, embeddings_path]
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def run_embeddings_with_progress(data_path, embeddings_path, city_label):
    if os.path.exists("/.dockerenv"):
        python_exec = "python"
    else:
        python_exec = ".venv/bin/python" if os.path.exists(".venv/bin/python") else "python3"

    cmd = [python_exec, "-u", "embed.py", data_path, embeddings_path]
    progress_bar = st.progress(0, text=f"Preparing embeddings for {city_label}...")
    status = st.empty()
    log_block = st.empty()
    logs = []
    total_batches = None

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    for raw_line in iter(process.stdout.readline, ""):
        line = raw_line.strip()
        if not line:
            continue

        logs.append(line)
        log_block.code("\n".join(logs[-20:]))

        found_match = re.search(
            r"Found\s+(\d+)\s+records.*batches of\s+(\d+)",
            line,
            re.IGNORECASE,
        )
        if found_match:
            total_records = int(found_match.group(1))
            batch_size = int(found_match.group(2))
            total_batches = max(1, (total_records + batch_size - 1) // batch_size)
            status.info(f"Embedding {total_records} records in {total_batches} batches.")
            progress_bar.progress(0, text=f"Starting embeddings for {city_label}...")
            continue

        batch_match = re.search(r"Processing batch\s+(\d+)", line, re.IGNORECASE)
        if batch_match and total_batches:
            current_batch = int(batch_match.group(1))
            progress = min(current_batch / total_batches, 1.0)
            progress_bar.progress(
                progress,
                text=f"Generating embeddings for {city_label}: batch {current_batch}/{total_batches}",
            )
            continue

        completed_match = re.search(r"Completed batch\s+(\d+)/(\d+)", line, re.IGNORECASE)
        if completed_match:
            completed_batches = int(completed_match.group(1))
            parsed_total_batches = int(completed_match.group(2))
            progress = min(completed_batches / parsed_total_batches, 1.0)
            progress_bar.progress(
                progress,
                text=f"Generating embeddings for {city_label}: {completed_batches}/{parsed_total_batches} batches done",
            )
            continue

        if "Saving final dataset with embeddings" in line:
            progress_bar.progress(0.98, text=f"Saving embeddings for {city_label}...")

    return_code = process.wait()
    combined_output = "\n".join(logs)

    if return_code != 0:
        progress_bar.empty()
        status.empty()
        raise subprocess.CalledProcessError(return_code, cmd, output=combined_output)

    progress_bar.progress(1.0, text=f"Embeddings ready for {city_label}.")
    status.success("Embedding job finished successfully.")
    return combined_output


@st.dialog("AI Settings")
def ai_settings_dialog():
    api_key = st.text_input(
        "OpenAI API Key",
        value=load_openai_api_key(),
        type="password",
        placeholder="sk-...",
    )

    if st.button("Save API Key", use_container_width=True, type="primary"):
        cleaned_key = api_key.strip()
        if not cleaned_key:
            st.error("Please enter a valid API key.")
        else:
            save_openai_api_key(cleaned_key)
            st.success("API key saved.")
            time.sleep(1)
            st.rerun()


if "use_test_dataset" not in st.session_state:
    st.session_state.use_test_dataset = False
if "selected_city" not in st.session_state:
    st.session_state.selected_city = "Köln"
if st.session_state.get("ui_state_version") != UI_STATE_VERSION:
    st.session_state["ui_state_version"] = UI_STATE_VERSION
    st.session_state["messages"] = []

sidebar_left, sidebar_right = st.sidebar.columns(2)
with sidebar_left:
    use_test_dataset = st.toggle(
        "Test mode",
        value=st.session_state.use_test_dataset,
        help="Switch the whole UI into test mode: use the test dataset and run crawls with the --test flag.",
    )
with sidebar_right:
    if st.button("AI Settings", use_container_width=True):
        ai_settings_dialog()

if use_test_dataset != st.session_state.use_test_dataset:
    st.session_state.use_test_dataset = use_test_dataset
    load_rag_chain.clear()
    st.rerun()

st.sidebar.caption(f"API Key: {mask_api_key(load_openai_api_key())}")

top_left, top_right = st.columns([3, 1])
with top_left:
    selected_city = st.selectbox(
        "Choose a city",
        CITY_OPTIONS,
        index=CITY_OPTIONS.index(st.session_state.selected_city),
        help="This is the main entry point: pick the city you want to explore or crawl.",
    )
with top_right:
    crawl_days = st.number_input("Days", min_value=1, max_value=30, value=14, step=1)

if selected_city != st.session_state.selected_city:
    st.session_state.selected_city = selected_city
    st.session_state.messages = []
    st.rerun()

dataset_config, dataset_summary, dataset_notice = choose_dataset(
    selected_city,
    st.session_state.use_test_dataset,
)
data_path = dataset_config["data_path"]
embeddings_path = dataset_config["embeddings_path"]

st.sidebar.info(
    f"{dataset_config['label']} dataset: "
    f"{(dataset_summary or {}).get('city') or 'Unavailable'} · "
    f"{(dataset_summary or {}).get('classes', 0)} classes · "
    f"{(dataset_summary or {}).get('venues', 0)} venues"
)

dataset_matches_selected_city = bool(
    dataset_summary and dataset_summary["city"] and dataset_summary["city"].lower() == selected_city.lower()
)

if dataset_notice:
    st.info(dataset_notice)

if dataset_matches_selected_city:
    st.success(f"Dataset available for {selected_city}.")
    stats = st.columns(5)
    stats[0].metric("Classes", f"{dataset_summary['classes']:,}")
    stats[1].metric("Venues", f"{dataset_summary['venues']:,}")
    stats[2].metric("Tokens", f"{dataset_summary['token_count']:,}")
    stats[3].metric("Embeddings", f"{dataset_summary['embedding_rows']:,}")
    embedding_dim_label = (
        f"{dataset_summary['embedding_dims']} dims"
        if dataset_summary["embedding_dims"]
        else "Not generated"
    )
    stats[4].metric("Embedding Size", embedding_dim_label)

    dataset_rows = [
        ("Mode", dataset_config["label"]),
        ("Dataset File", data_path),
        ("CSV Size", dataset_summary["data_size"]),
        ("Updated", dataset_summary["data_updated"]),
    ]
    embedding_rows = [
        ("Embeddings File", embeddings_path if dataset_summary["embedding_size"] else "Not generated yet"),
        ("File Size", dataset_summary["embedding_size"] or "Not generated yet"),
        ("Vector Size", f"{dataset_summary['embedding_dims']} dimensions" if dataset_summary["embedding_dims"] else "Not generated yet"),
    ]
    if dataset_summary["embedding_updated"]:
        embedding_rows.insert(3, ("Updated", dataset_summary["embedding_updated"]))

    col_dataset, col_embeddings = st.columns(2)
    with col_dataset:
        panel = st.container(border=True)
        panel.markdown("#### Dataset Overview est")
        for label, value in dataset_rows:
            lcol, rcol = panel.columns([1, 2])
            lcol.caption(label)
            rcol.markdown(f"**{value}**")
    with col_embeddings:
        panel = st.container(border=True)
        panel.markdown("#### Embeddings")
        for label, value in embedding_rows:
            lcol, rcol = panel.columns([1, 2])
            lcol.caption(label)
            rcol.markdown(f"**{value}**")

    action_left, action_right = st.columns([1, 1])
    with action_left:
        if st.button("Recrawl This City", type="secondary", use_container_width=True):
            try:
                logs = run_crawler_with_progress(selected_city, crawl_days, st.session_state.use_test_dataset)
                load_dataset_summary.clear()
                load_rag_chain.clear()
                count_city_venues.clear()
                st.success("Crawl completed successfully.")
                with st.expander("Crawler Logs"):
                    st.code(logs)
                time.sleep(1)
                st.rerun()
            except subprocess.CalledProcessError as e:
                st.error("Crawler failed.")
                st.code(e.stderr or e.stdout)
    with action_right:
        estimated_embedding_cost = estimate_embedding_cost_from_tokens(dataset_summary["token_count"])
        status_label = "Embeddings Ready" if dataset_summary["embedding_size"] else "Embeddings Missing"
        status_class = "pill-ok" if dataset_summary["embedding_size"] else "pill-missing"
        action_title = "Semantic Search is ready to use." if dataset_summary["embedding_size"] else "Create embeddings to unlock fast semantic search."
        st.markdown(
            f"""
            <div class="action-shell">
                <div class="action-topline">
                    <div>
                        <div class="action-eyebrow">Embedding Action</div>
                        <div class="action-title">{html.escape(action_title)}</div>
                    </div>
                    <div class="{status_class}">{html.escape(status_label)}</div>
                </div>
                <div class="action-caption">Estimated OpenAI embedding cost for the active dataset: ${html.escape(estimated_embedding_cost)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.caption("Embedding Action")
            st.markdown(
                "Semantic Search is ready to use." if dataset_summary["embedding_size"] else "Create embeddings to unlock fast semantic search."
            )
            status_label = "Embeddings Ready" if dataset_summary["embedding_size"] else "Embeddings Missing"
            st.status(status_label, state="complete" if dataset_summary["embedding_size"] else "warning")
            if dataset_summary["embedding_size"]:
                st.caption(f"Estimated embedding cost (current dataset): ${estimated_embedding_cost}")
            button_label = "Create Embeddings" if not dataset_summary["embedding_size"] else "Recreate Embeddings"
            button_type = "primary" if not dataset_summary["embedding_size"] else "secondary"
            if st.button(button_label, type=button_type, use_container_width=True):
                try:
                    logs = run_embeddings_with_progress(data_path, embeddings_path, selected_city)
                    load_dataset_summary.clear()
                    load_rag_chain.clear()
                    count_city_venues.clear()
                    st.success("Embeddings created successfully.")
                    with st.expander("Embedding Logs"):
                        st.code(logs)
                    time.sleep(1)
                    st.rerun()
                except subprocess.CalledProcessError as e:
                    st.error("Embedding generation failed.")
                    st.code(e.stderr or e.stdout)
else:
    st.warning(f"Attention: no saved dataset is available for {selected_city} yet.")

    estimate_col, start_col = st.columns([1, 1])
    with estimate_col:
        if st.button("Estimate Crawl Scope", type="primary", use_container_width=True):
            st.session_state["crawl_estimate_city"] = selected_city

    estimate_ready = st.session_state.get("crawl_estimate_city") == selected_city
    if estimate_ready:
        with st.spinner(f"Checking USC venue count for {selected_city}..."):
            venue_count = count_city_venues(selected_city)
            cost_estimate = estimate_embedding_cost_from_reference(
                venue_count,
                st.session_state.use_test_dataset,
            )

        est1, est2, est3 = st.columns(3)
        est1.metric("Venues To Fetch", f"{venue_count:,}")
        if cost_estimate:
            est2.metric("Estimated Tokens", f"{cost_estimate['estimated_tokens']:,}")
            est3.metric("Embedding Price Tag", f"${cost_estimate['estimated_cost']}")
            st.caption(
                f"Embedding estimate is based on average token density from the current "
                f"{cost_estimate['reference_city']} dataset."
            )
        else:
            est2.metric("Estimated Tokens", "Unknown")
            est3.metric("Embedding Price Tag", "Unknown")
            st.caption("Create one reference dataset first to enable price estimates.")

        with start_col:
            if st.button("Start Crawling", type="primary", use_container_width=True):
                try:
                    logs = run_crawler_with_progress(selected_city, crawl_days, st.session_state.use_test_dataset)
                    load_dataset_summary.clear()
                    load_rag_chain.clear()
                    count_city_venues.clear()
                    st.success("Crawl completed successfully.")
                    with st.expander("Crawler Logs"):
                        st.code(logs)
                    time.sleep(1)
                    st.rerun()
                except subprocess.CalledProcessError as e:
                    st.error("Crawler failed.")
                    st.code(e.stderr or e.stdout)
    else:
        st.info("Estimate the crawl first to see venue count and expected embedding spend.")


st.divider()
chat_header_left, chat_header_right = st.columns([3, 1])
with chat_header_left:
    st.subheader("Ask the Dataset")
    st.write("Use chat once the selected city has a local dataset available.")
    st.caption(f"Answers are generated with `{CHAT_MODEL}`.")
with chat_header_right:
    st.write("")
    st.write("")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

if dataset_matches_selected_city:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("grouped_results") is not None:
                render_result_groups(message["content"], message["grouped_results"])
            else:
                st.markdown(message["content"])

    if prompt := st.chat_input(f"E.g., Which yoga classes are available tomorrow evening in {selected_city}?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        rag_components = load_rag_chain(data_path, embeddings_path)
        if not rag_components:
            st.error("Failed to initialize RAG pipeline. Verify the dataset, embeddings, and API key.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing schedule..."):
                    try:
                        answer, documents = answer_question(rag_components, prompt)
                        grouped_results = build_result_groups(documents)
                        render_result_groups(answer, grouped_results)
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "grouped_results": grouped_results,
                            }
                        )
                    except Exception as e:
                        st.error(f"Chat error generated: {e}")
else:
    st.info("No local dataset is available for this city yet. Start a crawl above to unlock chat.")
