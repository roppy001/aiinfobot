import os

import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")


def load_sources() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
