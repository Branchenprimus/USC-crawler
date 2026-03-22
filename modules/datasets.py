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


def get_dataset_directory(city_name, use_test_data):
    return get_mode_root(use_test_data) / DATASET_DIRNAME / slugify_city(city_name)


def get_dataset_config(city_name, use_test_data):
    dataset_dir = get_dataset_directory(city_name, use_test_data)
    return {
        "label": "Test" if use_test_data else "Production",
        "city": city_name,
        "slug": slugify_city(city_name),
        "data_path": str(dataset_dir / "data.csv"),
        "embeddings_path": str(dataset_dir / "embeddings.json"),
        "dataset_dir": str(dataset_dir),
        "is_legacy": False,
    }


def get_legacy_dataset_config(use_test_data):
    root = get_mode_root(use_test_data)
    return {
        "label": "Test" if use_test_data else "Production",
        "city": None,
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
        for dataset_dir in sorted(
            (path for path in datasets_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        ):
            yield {
                "label": "Test" if use_test_data else "Production",
                "city": None,
                "slug": dataset_dir.name,
                "data_path": str(dataset_dir / "data.csv"),
                "embeddings_path": str(dataset_dir / "embeddings.json"),
                "dataset_dir": str(dataset_dir),
                "is_legacy": False,
            }

    legacy = get_legacy_dataset_config(use_test_data)
    if Path(legacy["data_path"]).exists():
        yield legacy
