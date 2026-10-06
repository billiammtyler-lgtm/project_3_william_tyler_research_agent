"""Validate the curated public portfolio offline, without model/API calls."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def code_hash(notebook):
    payload = [(cell.metadata.get("original_index"), cell.source)
               for cell in notebook.cells if cell.cell_type == "code"]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def main():
    manifest = json.loads((ROOT / "evidence/public_edition_manifest.json").read_text(encoding="utf-8"))
    sources = []
    for variant in ("High", "Low"):
        stem = f"William_Matthew_Tyler_Project_III_{variant}"
        notebook = nbformat.read(ROOT / "notebooks" / (stem + ".ipynb"), as_version=4)
        nbformat.validate(notebook)
        code = [cell for cell in notebook.cells if cell.cell_type == "code"]
        require(len(code) == 47, "Expected 47 implementation cells per notebook")
        require(all(not cell.outputs and cell.execution_count is None for cell in code),
                "Public notebook outputs/counters must be cleared")
        for cell in code:
            ast.parse(cell.source)
        require(code_hash(notebook) == manifest["notebooks"][variant]["code_source_sha256"],
                "Implementation code hash differs from the public-edition manifest")
        sources.append([(cell.metadata.original_index, cell.source) for cell in code])
        exported = (ROOT / "src" / (stem + ".py")).read_text(encoding="utf-8")
        ast.parse(exported)
        require(all(cell.source in exported for cell in code), "Python export missing notebook source")
        require((ROOT / "notebooks" / (stem + ".html")).is_file(), "HTML export missing")
    require(sources[0] == sources[1], "High/Low implementation source differs")

    records = json.loads((ROOT / "evaluation/evaluation_results.json").read_text(encoding="utf-8"))
    require(len(records) == 48, "Expected 48 answer records")
    require(len({(row["system"], row["id"]) for row in records}) == 48, "Duplicate benchmark roles")
    require(all(row["runtime_status"] == "completed" for row in records), "Incomplete generation record")
    require(all(row["judge_scored"] and row["judge_status"] == "scored" for row in records),
            "Expected 48 valid judge verdicts")
    require(all("expected_output" not in row for row in records), "Private reference answer included")
    for system, passes, expected_score in (("agent", 11, 0.75), ("naive_rag", 10, 0.5625)):
        subset = [row for row in records if row["system"] == system]
        require(len(subset) == 24 and sum(row["passed"] for row in subset) == passes,
                "Recorded rubric outcomes differ")
        mean = sum(row["judge_score"] for row in subset) / len(subset)
        require(abs(mean - expected_score) < 1e-10, "Recorded judge score differs")
    agreement = sum((row["judge_verdict"] == "correct") == row["passed"] for row in records)
    require(agreement == 40, "Recorded agreement differs")

    # Scan text artifacts; do not print any matching secret values.
    patterns = {
        "provider_credential": re.compile(r"\b(?:gl|tvly)-[A-Za-z0-9_+/=-]{16,}"),
        "openai_credential": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
        "personal_windows_path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+"),
        "private_colab_link": re.compile(r"colab\.research\.google\.com/drive/[A-Za-z0-9_-]+"),
        "private_drive_link": re.compile(r"drive\.google\.com/(?:file/d/|open\?id=)[A-Za-z0-9_-]+"),
    }
    hits = []
    text_files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix in {".py", ".md", ".json", ".csv", ".txt", ".html", ".ipynb"} or path.name == ".gitignore":
            text_files.append(path)
            text = path.read_text(encoding="utf-8")
            for name, pattern in patterns.items():
                if pattern.search(text):
                    hits.append({"file": path.relative_to(ROOT).as_posix(), "type": name})
        require(path.suffix.lower() not in {".pdf", ".zip", ".pem", ".key"}, "Private/raw input artifact included")
        require(path.name != "golden_dataset.csv", "Private evaluation dataset included")
    require(not hits, "Credential/private-path scan failed: " + json.dumps(hits))
    report = {
        "status": "passed", "api_calls": 0, "notebooks": 2, "code_cells_each": 47,
        "identical_implementation": True, "notebook_outputs_cleared": True,
        "answer_records": 48, "scored_judge_verdicts": 48, "rubric_passes": {"agent": 11, "naive_rag": 10},
        "agreement_count": agreement, "scanned_text_files": len(text_files), "credential_private_path_hits": [],
        "limits": ["Validates stored outcomes and public packaging; does not rerun models or authenticate source PDFs."],
    }
    (ROOT / "evidence/offline_portfolio_validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
