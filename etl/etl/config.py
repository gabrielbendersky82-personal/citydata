"""Load city adapter configs from etl/configs/*.yaml."""
from __future__ import annotations

import os
from typing import Any

import yaml

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")


def load_city(slug: str) -> dict[str, Any]:
    with open(os.path.join(CONFIG_DIR, f"{slug}.yaml")) as f:
        return yaml.safe_load(f)
