"""
MAPS Shield — full evaluation harness.

Runs a labelled dataset through the scanner and reports:

  1. Overall detection metrics (accuracy, precision, recall, F1, confusion matrix)
  2. Per-layer precision/recall/F1  <- these are the reliability inputs for noisy-OR
  3. Per-category breakdown         <- which attack types evade, which benign types false-positive
  4. Latency percentiles
  5. Layer-8 (LLM) invocation rate and failure rate
  6. Threshold sweep                <- what the tier boundaries should actually be
  7. Every misclassified prompt, so failures can be read rather than guessed at

Usage:
    python run_evaluation.py                          # defaults to eval_dataset.csv
    python run_evaluation.py --dataset path.csv
    python run_evaluation.py --limit 50               # quick smoke run
    python run_evaluation.py --out results/           # where to write artefacts

Dataset columns required: prompt, label (1=malicious, 0=benign)
Optional columns used if present: id, category, subcategory
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# All seven scoring layers, in pipeline order. Layer 7 (risk scoring) is the
# aggregator itself so it has no triggered/not-triggered state of its own.
LAYERS = [
    "keyword_detection",
    "regex_detection",
    "ngram_detection",
    "semantic_similarity",
    "ml_classifier",
    "rule_engine",
    "llm_classifier",
]


# ----------------------------------------------------------------- metrics

def prf(tp, fp, fn):
    """Precision, recall, F1 from raw counts. Returns zeros rather than NaN."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100)
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ----------------------------------------------------------------- tables

def table(headers, rows, aligns=None):
    """Render a fixed-width text table. No dependencies, copy-pastes into a report."""
    cols = len(headers)
    aligns = aligns or ["<"] * cols
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "  ".join("-" * w for w in widths)
    out = ["  ".join(f"{str(h):<{widths[i]}}" for i, h in enumerate(headers)), sep]
    for r in rows:
        out.append("  ".join(f"{str(c):{aligns[i]}{widths[i]}}" for i, c in enumerate(r)))
    return "\n".join(out)


def section(title):
    return f"\n{'=' * 78}\n{title}\n{'=' * 78}"


def md_table(headers, rows):
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def markdown_report(summary, res, y_true):
    """GitHub-renderable version of the same findings."""
    b = summary["BLOCK only"]
    w = summary["BLOCK or WARN"]
    md = ["# MAPS Shield — Evaluation Report", "",
          f"Dataset: {len(res)} prompts "
          f"({int(y_true.sum())} malicious, {int((1 - y_true).sum())} benign)", "",
          "## Headline", "",
          md_table(["Metric", "BLOCK only", "BLOCK or WARN"], [
              ["Accuracy", f"{b['accuracy']:.3f}", f"{w['accuracy']:.3f}"],
              ["Precision", f"{b['precision']:.3f}", f"{w['precision']:.3f}"],
              ["Recall", f"{b['recall']:.3f}", f"{w['recall']:.3f}"],
              ["F1", f"{b['f1']:.3f}", f"{w['f1']:.3f}"],
              ["Attacks missed (FN)", b["fn"], w["fn"]],
              ["Benign blocked (FP)", b["fp"], w["fp"]],
          ]), "",
          "## Per-layer performance", "",
          "Precision here is each layer's reliability input for noisy-OR scoring.", "",
          md_table(["Layer", "Fired", "Errors", "Precision", "Recall", "F1"],
                   [[k, v["fires"], v["errors"], f"{v['precision']:.3f}",
                     f"{v['recall']:.3f}", f"{v['f1']:.3f}"]
                    for k, v in summary["layers"].items()]), "",
          "## Per-category accuracy", ""]

    rows = []
    for (cat, sub), g in res.groupby(["category", "subcategory"], sort=True):
        n = len(g)
        blocked = int((g["decision"] == "BLOCK").sum())
        correct = blocked if g["label"].iloc[0] == 1 else n - blocked
        rows.append([cat, sub, n, correct, n - correct, f"{correct / n:.0%}",
                     f"{g['risk_score'].mean():.1f}"])
    md += [md_table(["Category", "Subcategory", "N", "Correct", "Wrong",
                     "Accuracy", "Mean score"], rows), "",
           "## Operational", "",
           md_table(["Metric", "Value"], [
               ["Latency p50", f"{summary['latency']['p50']:.1f} ms"],
               ["Latency p95", f"{summary['latency']['p95']:.1f} ms"],
               ["Latency p99", f"{summary['latency']['p99']:.1f} ms"],
               ["LLM invocation rate", f"{summary['llm_invocation_rate']:.1%}"],
               ["Resolved without API call", f"{1 - summary['llm_invocation_rate']:.1%}"],
               ["Best-F1 threshold", f"{summary['best_threshold']['threshold']} "
                                     f"(F1 {summary['best_threshold']['f1']:.3f})"],
           ]), "",
           "---", "",
           "Full detail including every misclassified prompt is in "
           "`evaluation_report.txt`; per-prompt results in "
           "`evaluation_predictions.csv`."]
    return "\n".join(md)


# ----------------------------------------------------------------- evaluation

def run(dataset_path, limit=None, out_dir=".", verbose=False):
    from backend.core.scanner import MAPSScanner

    df = pd.read_csv(dataset_path)
    if limit and limit < len(df):
        # Sample proportionally across categories. Taking head() would slice a
        # single category and give a wildly unrepresentative picture.
        if "category" in df.columns:
            df = (df.groupby("category", group_keys=False)
                    .apply(lambda g: g.sample(max(1, round(limit * len(g) / len(df))),
                                              random_state=42))
                    .reset_index(drop=True))
        else:
            df = df.sample(limit, random_state=42).reset_index(drop=True)
    if "category" not in df.columns:
        df["category"] = "uncategorised"
    if "subcategory" not in df.columns:
        df["subcategory"] = "uncategorised"
    if "id" not in df.columns:
        df["id"] = [f"R{i:04d}" for i in range(len(df))]

    print(f"Loaded {len(df)} prompts from {dataset_path}")
    print(f"  malicious: {int(df['label'].sum())}   benign: {int((1 - df['label']).sum())}")
    print("\nInitialising scanner (first run loads the transformer, this takes a moment)...")

    scanner = MAPSScanner()
    scanner.scan("warmup")  # keep the cold-start cost out of the latency numbers

    records = []
    t_start = time.time()
    for n, (_, row) in enumerate(df.iterrows(), start=1):
        result = scanner.scan(str(row["prompt"]), detailed=True)

        triggered = {}
        confidences = {}
        errored = {}
        for lr in result.get("layer_results") or []:
            name = lr.get("layer")
            triggered[name] = bool(lr.get("triggered"))
            confidences[name] = float(lr.get("confidence") or 0.0)
            errored[name] = bool(lr.get("error"))

        records.append({
            "id": row["id"],
            "prompt": row["prompt"],
            "label": int(row["label"]),
            "category": row["category"],
            "subcategory": row["subcategory"],
            "decision": result["decision"],
            "classification": result["classification"],
            "risk_score": result["risk_score"],
            "scan_time_ms": result["scan_time_ms"],
            "llm_invoked": bool(result.get("llm_invoked")),
            **{f"trig_{l}": triggered.get(l, False) for l in LAYERS},
            **{f"conf_{l}": confidences.get(l, 0.0) for l in LAYERS},
            **{f"err_{l}": errored.get(l, False) for l in LAYERS},
        })

        if n % 25 == 0 or n == len(df):
            elapsed = time.time() - t_start
            rate = n / elapsed if elapsed else 0
            print(f"  {n}/{len(df)} scanned  ({rate:.1f}/s)")

    res = pd.DataFrame(records)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "evaluation_predictions.csv", index=False)

    report = []
    summary = {}

    # ---------------------------------------------------- 1. overall
    y_true = res["label"].values
    pred_block = (res["decision"] == "BLOCK").astype(int).values
    pred_block_or_warn = res["decision"].isin(["BLOCK", "WARN"]).astype(int).values

    def confusion(pred):
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        tn = int(((pred == 0) & (y_true == 0)).sum())
        return tp, fp, fn, tn

    report.append(section("1. OVERALL DETECTION PERFORMANCE"))
    rows = []
    for name, pred in [("BLOCK only", pred_block), ("BLOCK or WARN", pred_block_or_warn)]:
        tp, fp, fn, tn = confusion(pred)
        p, r, f1 = prf(tp, fp, fn)
        acc = (tp + tn) / len(y_true)
        rows.append([name, f"{acc:.3f}", f"{p:.3f}", f"{r:.3f}", f"{f1:.3f}", tp, fp, fn, tn])
        summary[name] = {"accuracy": acc, "precision": p, "recall": r, "f1": f1,
                         "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    report.append(table(
        ["Treated as positive", "Accuracy", "Precision", "Recall", "F1", "TP", "FP", "FN", "TN"],
        rows, ["<", ">", ">", ">", ">", ">", ">", ">", ">"]))
    report.append(
        "\nPrecision = of everything blocked, how much was actually malicious."
        "\nRecall    = of all malicious prompts, how many were caught."
        "\nFN here are attacks that reached the model. FP are legitimate users turned away.")

    # ---------------------------------------------------- 2. per-layer
    report.append(section("2. PER-LAYER PERFORMANCE  (reliability inputs for noisy-OR)"))
    rows = []
    layer_stats = {}
    for layer in LAYERS:
        t = res[f"trig_{layer}"].astype(int).values
        tp = int(((t == 1) & (y_true == 1)).sum())
        fp = int(((t == 1) & (y_true == 0)).sum())
        fn = int(((t == 0) & (y_true == 1)).sum())
        p, r, f1 = prf(tp, fp, fn)
        fires = int(t.sum())
        errs = int(res[f"err_{layer}"].sum())
        mean_conf = res.loc[res[f"trig_{layer}"], f"conf_{layer}"].mean()
        mean_conf = 0.0 if pd.isna(mean_conf) else mean_conf
        rows.append([layer, fires, errs, f"{p:.3f}", f"{r:.3f}", f"{f1:.3f}", f"{mean_conf:.3f}"])
        layer_stats[layer] = {"fires": fires, "errors": errs, "precision": p,
                              "recall": r, "f1": f1, "mean_confidence_when_fired": mean_conf}
    report.append(table(
        ["Layer", "Fired", "Errors", "Precision", "Recall", "F1", "Mean conf"],
        rows, ["<", ">", ">", ">", ">", ">", ">"]))
    report.append(
        "\nPrecision here is the number to use as each layer's reliability r_i in"
        "\n    P(malicious) = 1 - PROD(1 - c_i * r_i)"
        "\nA layer that fires often but with low precision should carry a low reliability,"
        "\nregardless of the weight it currently has in default_config.yaml.")
    summary["layers"] = layer_stats

    # ---------------------------------------------------- 3. per-category
    report.append(section("3. PER-CATEGORY BREAKDOWN"))
    rows = []
    for (cat, sub), g in res.groupby(["category", "subcategory"], sort=True):
        n = len(g)
        if g["label"].iloc[0] == 1:
            caught = int((g["decision"] == "BLOCK").sum())
            missed = n - caught
            rows.append([cat, sub, n, caught, missed, f"{caught / n:.1%}", f"{g['risk_score'].mean():.1f}"])
        else:
            blocked = int((g["decision"] == "BLOCK").sum())
            rows.append([cat, sub, n, n - blocked, blocked, f"{(n - blocked) / n:.1%}", f"{g['risk_score'].mean():.1f}"])
    report.append(table(
        ["Category", "Subcategory", "N", "Correct", "Wrong", "Accuracy", "Mean score"],
        rows, ["<", "<", ">", ">", ">", ">", ">"]))
    report.append(
        "\nFor malicious rows, Wrong = attacks that got through."
        "\nFor benign rows, Wrong = legitimate prompts that were blocked.")

    # ---------------------------------------------------- 4. latency
    report.append(section("4. LATENCY"))
    all_t = res["scan_time_ms"].tolist()
    no_llm = res.loc[~res["llm_invoked"], "scan_time_ms"].tolist()
    with_llm = res.loc[res["llm_invoked"], "scan_time_ms"].tolist()
    rows = []
    for name, vals in [("All scans", all_t), ("Without LLM layer", no_llm), ("With LLM layer", with_llm)]:
        if vals:
            rows.append([name, len(vals), f"{percentile(vals, 50):.1f}",
                         f"{percentile(vals, 95):.1f}", f"{percentile(vals, 99):.1f}",
                         f"{max(vals):.1f}"])
    report.append(table(["Subset", "N", "p50 ms", "p95 ms", "p99 ms", "max ms"],
                        rows, ["<", ">", ">", ">", ">", ">"]))
    summary["latency"] = {"p50": percentile(all_t, 50), "p95": percentile(all_t, 95),
                          "p99": percentile(all_t, 99)}

    # ---------------------------------------------------- 5. LLM gating
    report.append(section("5. LAYER 8 GATING  (the cost-saving claim)"))
    invoked = int(res["llm_invoked"].sum())
    failed = int(res["err_llm_classifier"].sum())
    rows = [
        ["Prompts scanned", len(res), ""],
        ["LLM invoked", invoked, f"{invoked / len(res):.1%}"],
        ["LLM skipped", len(res) - invoked, f"{(len(res) - invoked) / len(res):.1%}"],
        ["LLM calls that errored", failed, f"{failed / invoked:.1%}" if invoked else "n/a"],
    ]
    report.append(table(["Metric", "Count", "Share"], rows, ["<", ">", ">"]))
    report.append(
        f"\n{(len(res) - invoked) / len(res):.1%} of prompts resolved without an API call."
        "\nThat is the measured version of the gating claim.")
    summary["llm_invocation_rate"] = invoked / len(res) if len(res) else 0

    # ---------------------------------------------------- 6. threshold sweep
    report.append(section("6. THRESHOLD SWEEP  (where the tier boundaries should sit)"))
    rows = []
    best = (0, -1)
    for thr in range(0, 101, 5):
        pred = (res["risk_score"] >= thr).astype(int).values
        tp = int(((pred == 1) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        fn = int(((pred == 0) & (y_true == 1)).sum())
        p, r, f1 = prf(tp, fp, fn)
        rows.append([thr, f"{p:.3f}", f"{r:.3f}", f"{f1:.3f}", fp, fn])
        if f1 > best[1]:
            best = (thr, f1)
    report.append(table(["Score >=", "Precision", "Recall", "F1", "FP", "FN"],
                        rows, [">", ">", ">", ">", ">", ">"]))
    report.append(f"\nBest F1 at threshold {best[0]} (F1 = {best[1]:.3f})."
                  f"\nCurrent config blocks at 51. Compare.")
    summary["best_threshold"] = {"threshold": best[0], "f1": best[1]}

    # ---------------------------------------------------- 7. errors
    report.append(section("7. MISCLASSIFIED PROMPTS"))
    fns = res[(res["label"] == 1) & (res["decision"] != "BLOCK")]
    fps = res[(res["label"] == 0) & (res["decision"] == "BLOCK")]

    report.append(f"\nFALSE NEGATIVES — attacks that reached the model ({len(fns)}):\n")
    if len(fns):
        report.append(table(
            ["ID", "Subcategory", "Score", "Decision", "Prompt"],
            [[r["id"], r["subcategory"], r["risk_score"], r["decision"],
              (r["prompt"][:68] + "...") if len(r["prompt"]) > 68 else r["prompt"]]
             for _, r in fns.iterrows()],
            ["<", "<", ">", "<", "<"]))
    else:
        report.append("  none")

    report.append(f"\n\nFALSE POSITIVES — legitimate prompts blocked ({len(fps)}):\n")
    if len(fps):
        report.append(table(
            ["ID", "Subcategory", "Score", "Decision", "Prompt"],
            [[r["id"], r["subcategory"], r["risk_score"], r["decision"],
              (r["prompt"][:68] + "...") if len(r["prompt"]) > 68 else r["prompt"]]
             for _, r in fps.iterrows()],
            ["<", "<", ">", "<", "<"]))
    else:
        report.append("  none")

    # ---------------------------------------------------- write
    text = "\n".join(report)
    (out / "evaluation_report.txt").write_text(text, encoding="utf-8")
    (out / "evaluation_report.md").write_text(markdown_report(summary, res, y_true), encoding="utf-8")
    if verbose:
        print(text)
    (out / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # ---------------------------------------------------- console summary
    b = summary["BLOCK only"]
    print(f"\n{'-' * 60}")
    print(f"  Scanned        {len(res)} prompts "
          f"({int(y_true.sum())} malicious, {int((1 - y_true).sum())} benign)")
    print(f"  Precision      {b['precision']:.3f}")
    print(f"  Recall         {b['recall']:.3f}      <- share of attacks caught")
    print(f"  F1             {b['f1']:.3f}")
    print(f"  Missed attacks {b['fn']}")
    print(f"  False blocks   {b['fp']}")
    print(f"  Latency p50    {summary['latency']['p50']:.1f} ms   p95 {summary['latency']['p95']:.1f} ms")
    print(f"  LLM invoked    {summary['llm_invocation_rate']:.1%} of prompts")
    print(f"{'-' * 60}")
    print("\nReports written:")
    print(f"  {out / 'evaluation_report.md'}         readable report (renders on GitHub)")
    print(f"  {out / 'evaluation_report.txt'}        plain-text version")
    print(f"  {out / 'evaluation_predictions.csv'}   per-prompt results")
    print(f"  {out / 'evaluation_summary.json'}      machine-readable summary")
    print("\nRe-run with --verbose to print the full report here as well.")


def main():
    ap = argparse.ArgumentParser(description="Evaluate MAPS Shield against a labelled dataset.")
    ap.add_argument("--dataset", default="eval_dataset.csv")
    ap.add_argument("--limit", type=int, default=None, help="only scan the first N rows")
    ap.add_argument("--out", default=".", help="directory for report artefacts")
    ap.add_argument("--verbose", action="store_true",
                    help="also print the full report to the terminal (default: files only)")
    args = ap.parse_args()

    if not Path(args.dataset).exists():
        sys.exit(f"dataset not found: {args.dataset}")
    run(args.dataset, args.limit, args.out, args.verbose)


if __name__ == "__main__":
    main()