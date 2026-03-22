from pathlib import Path
import re
import unicodedata


DATASET_DIRNAME = "datasets"


def slugify_city(city_name):
    if not city_name:
        return "custom"

    normalized = unicodedata.normalize("NFKD", city_name)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "custom"


def get_mode_root(use_test_data):
    return Path("test" if use_test_data else "output")


def normalize_contract(contract):
    return (contract or "m").strip().lower()


def get_dataset_directory(city_name, use_test_data, contract="m"):
    return (
        get_mode_root(use_test_data)
        / DATASET_DIRNAME
        / slugify_city(city_name)
        / normalize_contract(contract)
    )


def get_dataset_config(city_name, use_test_data, contract="m"):
    contract_slug = normalize_contract(contract)
    dataset_dir = get_dataset_directory(city_name, use_test_data, contract_slug)
    return {
        "label": "Test" if use_test_data else "Production",
        "city": city_name,
        "contract": contract_slug.upper(),
        "slug": slugify_city(city_name),
        "data_path": str(dataset_dir / "data.csv"),
        "embeddings_path": str(dataset_dir / "embeddings.json"),
        "dataset_dir": str(dataset_dir),
        "is_legacy": False,
    }


def get_legacy_city_dataset_config(city_name, use_test_data, contract="m"):
    city_dir = get_mode_root(use_test_data) / DATASET_DIRNAME / slugify_city(city_name)
    return {
        "label": "Test" if use_test_data else "Production",
        "city": city_name,
        "contract": normalize_contract(contract).upper(),
        "slug": slugify_city(city_name),
        "data_path": str(city_dir / "data.csv"),
        "embeddings_path": str(city_dir / "embeddings.json"),
        "dataset_dir": str(city_dir),
        "is_legacy": True,
    }


def get_legacy_dataset_config(use_test_data):
    root = get_mode_root(use_test_data)
    return {
        "label": "Test" if use_test_data else "Production",
        "city": None,
        "contract": "M",
        "slug": "legacy",
        "data_path": str(root / "data.csv"),
        "embeddings_path": str(root / "embeddings.json"),
        "dataset_dir": str(root),
        "is_legacy": True,
    }


def iter_dataset_configs(use_test_data):
    root = get_mode_root(use_test_data)
    datasets_root = root / DATASET_DIRNAME

    if datasets_root.exists():
        for city_dir in sorted(
            (path for path in datasets_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            legacy_data = city_dir / "data.csv"
            if legacy_data.exists():
                yield {
                    "label": "Test" if use_test_data else "Production",
                    "city": None,
                    "contract": "M",
                    "slug": city_dir.name,
                    "data_path": str(legacy_data),
                    "embeddings_path": str(city_dir / "embeddings.json"),
                    "dataset_dir": str(city_dir),
                    "is_legacy": True,
                }

            for contract_dir in sorted(
                (path for path in city_dir.iterdir() if path.is_dir()),
                key=lambda path: path.name,
            ):
                yield {
                    "label": "Test" if use_test_data else "Production",
                    "city": None,
                    "contract": contract_dir.name.upper(),
                    "slug": city_dir.name,
                    "data_path": str(contract_dir / "data.csv"),
                    "embeddings_path": str(contract_dir / "embeddings.json"),
                    "dataset_dir": str(contract_dir),
                    "is_legacy": False,
                }

    legacy = get_legacy_dataset_config(use_test_data)
    if Path(legacy["data_path"]).exists():
        yield legacy
