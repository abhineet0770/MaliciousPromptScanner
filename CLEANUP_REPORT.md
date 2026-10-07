# Repository Cleanup Report (MAPS Shield)

This document details the mechanical cleanup performed on the **MAPS Shield** repository according to industry standards, without modifying detection logic, scoring weights, thresholds, data files, or deleting any candidate files.

---

## 1. Summary of Changes per Phase

### Phase 1 — Dead Code Cleanup
- **Commit:** `803767e` — *Remove unused imports and dead locals*
- **Changes & Counts:**
  - **14 unused imports removed** across 8 files:
    - `backend/detection/keyword_detector.py`: removed `import re`
    - `backend/detection/llm_classifier.py`: removed `Optional` from `typing`
    - `backend/detection/ml_classifier.py`: removed `List` from `typing` (preserved 3 `sklearn` availability probes)
    - `backend/detection/risk_scoring.py`: removed `import json`
    - `backend/detection/rule_engine.py`: removed `import json`
    - `backend/detection/semantic_detector.py`: removed `import json` and unused `import numpy as np`
    - `scripts/expand_datasets.py`: removed `import random`
    - `start.py`: removed `from pathlib import Path`
    - `tests/evaluate.py`: removed `List` and `classification_report`
    - `train_models.py`: removed `from backend.detection.ml_classifier import MLClassifier`
  - **1 swallowed exception logged** instead of discarded:
    - `backend/detection/llm_classifier.py:136`: captured and logged `e` in `logger.warning(...)` during provider `ImportError`.
  - **1 unused loop variable fixed:**
    - `scripts/expand_datasets.py:102`: iterated over `keywords.values()` instead of unused dict key tuple.

### Phase 2 — Exception Chaining
- **Commit:** `9e9fbf8` — *Chain exceptions in API error handlers*
- **Changes & Counts:**
  - **5 HTTP exceptions chained** with `from e` in `backend/api/main.py`:
    - `scan_prompt` endpoint (line 230)
    - `scan_batch` endpoint (line 258)
    - `get_statistics` endpoint (line 272)
    - `get_recent_scans` endpoint (line 286)
    - `get_trends` endpoint (line 300)

### Phase 3 — Test Assertion & Failure Capability
- **Commit:** `12a4595` — *Make test_quick.py assert expected decisions instead of printing*
- **Changes & Counts:**
  - Converted `test_quick.py` to compare scan results against expected decisions (`assert result['decision'] == expected_decision`).
  - Added assertions to detector checks (`result['triggered'] is True`).
  - Removed unused dead variable `test_prompts`.
  - Replaced raw module imports with dynamic `importlib.import_module` iteration to test module importability cleanly without lint warnings.
  - Returns exit code `1` on any assertion or test failure and `0` on success.

### Phase 4 — Ambiguity Band Standardization
- **Commit:** `eaaef9d` — *Standardize LLM ambiguity band to 5-60 across config, code and docs*
- **Changes & Counts:**
  - Standardized the Layer 8 LLM ambiguity band to **5–60** across all repository layers:
    - `backend/detection/llm_classifier.py`: updated docstring from `15–60` to `5–60`.
    - `backend/detection/llm_classifier.py:98`: changed fallback default from `15` to `5` (`cfg.get("ambiguity_threshold_low", 5)`).
    - `README.md`: updated Mermaid architecture diagram from `0-80` / `> 80` to `5-60` / `> 60`.
  - Maintained `config/default_config.yaml` as the canonical source (`5` to `60`).

### Phase 5 — Project Configuration & Line Endings
- **Commit:** `782e789` — *Add ruff config and line-ending normalization*
- **Changes & Counts:**
  - Created `pyproject.toml` with Ruff configuration targeting Python 3.11, line-length 100, and rule sets `["E", "F", "W", "B", "I"]`.
  - Updated `.gitattributes` to include `* text=auto eol=lf` before existing Git LFS entries (`models/*.pkl`, `models/*.npy`).

---

## 2. Ruff Check Statistics (Before vs. After)

### Dead Code Rule Set (`--select=F401,F841,B007`)

**Before:**
```text
26	F401	[-] unused-import
 2	B007	[ ] unused-loop-control-variable
 2	F841	[-] unused-variable
Found 30 errors.
```

**After:**
```text
3	F401	unused-import
Found 3 errors.
```
*(Note: The 3 remaining `F401` errors are the intentional `sklearn` availability probes in `backend/detection/ml_classifier.py:43-45`).*

### Global Linter Output (`ruff check . --statistics`)

**Before Cleanup (Default Profile):**
```text
102	UP006  	[*] non-pep585-annotation
 36	I001   	[*] unsorted-imports
 32	UP045  	[*] non-pep604-annotation-optional
 30	BLE001 	[ ] blind-except
 26	UP035  	[-] deprecated-import
 26	F401   	[-] unused-import
 10	RUF012 	[ ] mutable-class-default
  6	C408   	[ ] unnecessary-collection-call
  5	E722   	[ ] bare-except
  5	RUF010 	[*] explicit-f-string-type-conversion
  4	RUF013 	[ ] implicit-optional
  3	DTZ005 	[ ] call-datetime-now-without-tzinfo
  2	SIM115 	[ ] open-file-with-context-handler
  2	FURB188	[*] slice-to-remove-prefix-or-suffix
  2	PLW1510	[ ] subprocess-run-without-check
  2	S110   	[ ] try-except-pass
  2	F841   	[-] unused-variable
  1	DTZ006 	[ ] call-datetime-fromtimestamp
  1	SIM102 	[ ] collapsible-if
  1	UP007  	[*] non-pep604-annotation-union
  1	C401   	[ ] unnecessary-generator-set
  1	RUF022 	[*] unsorted-dunder-all
Found 300 errors.
```

**After Cleanup (Configured `pyproject.toml` Rule Sets `[E, F, W, B, I]`):**
```text
410	W293	[-] blank-line-with-whitespace
100	E501	[ ] line-too-long
 32	I001	[*] unsorted-imports
  6	E402	[ ] module-import-not-at-top-of-file
  6	W291	[*] trailing-whitespace
  5	E722	[ ] bare-except
  4	W292	[*] missing-newline-at-end-of-file
  3	F401	[ ] unused-import
  1	E741	[ ] ambiguous-variable-name
  1	E401	[*] multiple-imports-on-one-line
Found 568 errors.
```

---

## 3. Phase 6: Candidate Files Audit

No files were deleted in this pass. The table below audits candidate files for future human decision:

| File Path | Size (Bytes / Lines) | Referenced in Repo? | Grep Evidence | Recommendation | Reason |
|---|---|---|---|---|---|
| `patch_keywords.py` | 3,261 B / 89 L | **No** | 0 references across repo | **SAFE TO DELETE** | One-off historical patch script that modified `data/keywords.json` in-place. |
| `patch_keywords2.py` | 4,326 B / 97 L | **No** | 0 references across repo | **SAFE TO DELETE** | One-off historical patch script for social engineering keywords into `data/keywords.json`. |
| `demo.py` | 3,931 B / 118 L | **No** | 0 references across repo | **SAFE TO DELETE** | Standalone demo script with hardcoded test cases. Redundant with `start.py` and `test_quick.py`. |
| `start.py` | 2,758 B / 105 L | **Yes** | `README.md:127` (`python start.py --all`), `README.md:224` | **KEEP** | Documented primary launcher CLI for running FastAPI API server and Streamlit dashboard. |
| `scripts/expand_datasets.py` | 10,032 B / 204 L | **Yes** | `README.md:220`, `README.md:252` (`python scripts/expand_datasets.py`) | **KEEP** | Documented generator utility to expand combinatorial attack keywords. |
| `scripts/extract_data_to_files.py` | 1,785 B / 43 L | **No** | 0 references across repo (only self-comment) | **SAFE TO DELETE** | One-off data extraction script used to migrate detector class constants to JSON files. |
| `scripts/download_models.py` | 486 B / 16 L | **Yes** | `Dockerfile:26` (`RUN python scripts/download_models.py \|\| true`), `README.md:92` | **KEEP** | Used in Docker build and manual non-LFS setup to download transformer models. |

---

## 4. How to Restore

If any phase needs to be reverted, each individual commit can be reverted independently using `git revert`:

| Phase | Commit Hash | Revert Command |
|---|---|---|
| Phase 1: Dead code & unused imports | `803767e` | `git revert 803767e` |
| Phase 2: Exception chaining in API | `9e9fbf8` | `git revert 9e9fbf8` |
| Phase 3: Assertions in `test_quick.py` | `12a4595` | `git revert 12a4595` |
| Phase 4: Ambiguity band standardization | `eaaef9d` | `git revert eaaef9d` |
| Phase 5: Ruff config & `.gitattributes` | `782e789` | `git revert 782e789` |
| Final Deliverable: Cleanup report | `cbed886` | `git revert cbed886` |

To restore the entire repository to the state prior to this cleanup pass:
```bash
git revert --no-commit 803767e..HEAD
git commit -m "Revert cleanup pass"
```
