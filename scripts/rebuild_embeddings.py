"""
Rebuild semantic embeddings cache from data/attack_examples.json.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from backend.detection.semantic_detector import SemanticDetector  # noqa: E402


def rebuild_embeddings():
    data_path = PROJECT_ROOT / "data" / "attack_examples.json"
    cache_path = PROJECT_ROOT / "models" / "semantic_embeddings.npy"
    config_path = PROJECT_ROOT / "config" / "default_config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception:
        config_data = {}

    sem_config = config_data.get("semantic_detector", {}) if isinstance(config_data, dict) else {}
    model_name = sem_config.get("model_name", "all-MiniLM-L6-v2")
    device = sem_config.get("device", "cpu")

    print(f"Loading attack examples from {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        attack_examples = json.load(f)

    # Before stats
    before_count = 0
    before_size = 0
    if cache_path.exists():
        before_size = os.path.getsize(cache_path)
        try:
            old_data = np.load(cache_path, allow_pickle=True).item()
            before_count = len(old_data.get("attack_examples", []))
        except Exception as e:
            print(f"Warning: Could not read existing cache: {e}")

    print("\n--- BEFORE REBUILD ---")
    print(f"Existing cache path: {cache_path}")
    print(f"Cached attack examples count: {before_count}")
    print(f"Cache file size: {before_size} bytes ({before_size / 1024:.2f} KB)")

    print(f"\nConstructing SemanticDetector (model={model_name}, without loading cache)...")
    detector = SemanticDetector(model_name=model_name, device=device, load_cache=False)
    detector.attack_examples = attack_examples

    print(f"Computing embeddings for {len(attack_examples)} examples...")
    detector._compute_attack_embeddings()

    print(f"Saving embeddings to {cache_path}...")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    detector.save_embeddings(cache_path)

    # After stats
    after_size = os.path.getsize(cache_path)
    new_data = np.load(cache_path, allow_pickle=True).item()
    after_count = len(new_data.get("attack_examples", []))

    mb_size = after_size / (1024 * 1024)
    print("\n--- AFTER REBUILD ---")
    print(f"New cached model name: {new_data.get('model_name')}")
    print(f"New cached attack examples count: {after_count}")
    print(f"New cache file size: {after_size} bytes ({after_size / 1024:.2f} KB, {mb_size:.2f} MB)")
    print("Rebuild complete!")


if __name__ == "__main__":
    rebuild_embeddings()
