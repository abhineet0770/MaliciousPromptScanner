"""
Similarity Threshold Sweep Script
=================================
Sweeps cosine similarity thresholds (0.30 to 0.80 in 0.05 steps) on tests/eval_dataset.csv
for the Semantic Similarity layer alone and prints precision, recall, and F1.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics.pairwise import cosine_similarity  # noqa: E402

from backend.detection.semantic_detector import SemanticDetector  # noqa: E402


def sweep_similarity(dataset_path: Path = None):
    if dataset_path is None:
        dataset_path = PROJECT_ROOT / "tests" / "eval_dataset.csv"

    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)

    prompts = df["prompt"].tolist()
    labels = df["label"].to_numpy()
    total_samples = len(df)
    total_malicious = int(labels.sum())
    total_benign = total_samples - total_malicious

    print(f"Loaded {total_samples} samples ({total_malicious} malicious, {total_benign} benign).")

    print("\nInitializing SemanticDetector...")
    detector = SemanticDetector()
    print(f"Detector initialized with {len(detector.attack_examples)} attack examples.")

    if not detector.use_embeddings or detector.model is None:
        print("Error: Semantic detector could not initialize embeddings model.")
        sys.exit(1)

    print(f"Encoding {len(prompts)} prompts from evaluation dataset...")
    prompt_embeddings = detector.model.encode(
        prompts,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    print("Computing cosine similarity matrix...")
    sim_matrix = cosine_similarity(prompt_embeddings, detector.attack_embeddings)
    max_similarities = np.max(sim_matrix, axis=1)

    thresholds = [round(t, 2) for t in np.arange(0.30, 0.801, 0.05)]

    print("\n" + "=" * 76)
    headers = (
        f"{'Threshold':>10} | {'Fired':>6} | {'Precision':>10} | "
        f"{'Recall':>8} | {'F1':>8} | {'TP':>5} | {'FP':>5} | {'FN':>5}"
    )
    print(headers)
    print("-" * 76)

    for t in thresholds:
        preds = (max_similarities >= t).astype(int)
        tp = int(np.sum((preds == 1) & (labels == 1)))
        fp = int(np.sum((preds == 1) & (labels == 0)))
        fn = int(np.sum((preds == 0) & (labels == 1)))

        fired = tp + fp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        row = (
            f"{t:>10.2f} | {fired:>6} | {precision:>10.4f} | "
            f"{recall:>8.4f} | {f1:>8.4f} | {tp:>5} | {fp:>5} | {fn:>5}"
        )
        print(row)

    print("=" * 76 + "\n")


if __name__ == "__main__":
    sweep_similarity()
