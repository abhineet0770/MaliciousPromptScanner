"""
Extract existing hardcoded data from detectors into data/ JSON files.
Run once: python scripts/extract_data_to_files.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# L1: Keywords
from backend.detection.keyword_detector import KeywordDetector

kd = KeywordDetector()
with open(DATA / "keywords.json", "w", encoding="utf-8") as f:
    json.dump(kd.keywords, f, indent=2, ensure_ascii=False)
print(f"[OK] keywords.json — {sum(len(v) for v in kd.keywords.values())} keywords")

# L2: Regex patterns
from backend.detection.regex_detector import RegexDetector

patterns = [
    {"name": p["name"], "pattern": p["pattern"], "category": p["category"],
     "severity": p["severity"], "description": p["description"]}
    for p in RegexDetector.DEFAULT_PATTERNS
]
with open(DATA / "regex_patterns.json", "w", encoding="utf-8") as f:
    json.dump(patterns, f, indent=2, ensure_ascii=False)
print(f"[OK] regex_patterns.json — {len(patterns)} patterns")

# L3: N-gram templates
from backend.detection.ngram_detector import NGramDetector

with open(DATA / "ngram_templates.json", "w", encoding="utf-8") as f:
    json.dump(NGramDetector.DEFAULT_TEMPLATES, f, indent=2, ensure_ascii=False)
print(f"[OK] ngram_templates.json — {len(NGramDetector.DEFAULT_TEMPLATES)} templates")

# L4: Semantic attack examples
from backend.detection.semantic_detector import SemanticDetector

with open(DATA / "attack_examples.json", "w", encoding="utf-8") as f:
    json.dump(SemanticDetector.DEFAULT_ATTACK_EXAMPLES, f, indent=2, ensure_ascii=False)
print(f"[OK] attack_examples.json — {len(SemanticDetector.DEFAULT_ATTACK_EXAMPLES)} examples")

print("\nAll data files created in data/")
