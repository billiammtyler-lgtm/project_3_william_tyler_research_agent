"""Create a public portfolio edition from completed local Project III artifacts.

No API calls or notebook execution. Originals stay untouched. This export clears
notebook outputs, removes course reference answers and summarizes raw contexts.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

OMITTED_KEYS = {"expected_output", "reference_answer", "reference", "golden_answer"}
HEADINGS = {
    13: "Environment and model configuration", 39: "Live web-search tool",
    45: "Document ingestion and MMR retrieval", 62: "Tool binding and routing checks",
    71: "Manual LangGraph research agent", 87: "Answer execution and trajectories",
    93: "Naive RAG baseline", 97: "Initial system comparisons",
    102: "Report generation", 114: "Evaluation inputs and source audit",
    119: "Checkpointed benchmark execution", 122: "Deterministic answer and evidence checks",
    132: "Structured model judge", 139: "Scorecards and denominators",
    143: "Judge agreement", 146: "Failure diagnosis", 150: "Final scorecard display",
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def code_hash(notebook):
    payload = [(c.metadata.get("original_index"), c.source)
               for c in notebook.cells if c.cell_type == "code"]
    return sha(json.dumps(payload, ensure_ascii=False))


def redact_string(value):
    # Personal-machine paths are provenance, not portable configuration.
    def relative_path(match):
        raw = match.group(0).replace("\\", "/")
        if "/Output/" in raw:
            return "[LOCAL_OUTPUT]/" + raw.split("/Output/", 1)[1]
        if "/project3_work/" in raw:
            return "[LOCAL_WORKSPACE]/" + raw.split("/project3_work/", 1)[1]
        return "[LOCAL_PATH]/" + raw.rsplit("/", 1)[-1]
    value = re.sub(r"[A-Za-z]:[\\/]Users[\\/][^\r\n\"<>|]+", relative_path, value)
    value = re.sub(r"https://colab\.research\.google\.com/drive/[A-Za-z0-9_-]+",
                   "[PRIVATE_COLAB_LINK_OMITTED]", value)
    value = re.sub(r"https://drive\.google\.com/(?:file/d/|open\?id=)[A-Za-z0-9_-]+",
                   "[PRIVATE_DRIVE_LINK_OMITTED]", value)
    return value


def sanitize(value):
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in OMITTED_KEYS:
                continue
            if key == "excerpt" or key.endswith("_excerpt"):
                result[key + "_summary"] = {"characters": len(str(item)), "content_sha256": sha(str(item)),
                                            "raw_text_included": False}
            else:
                result[key] = sanitize(item)
        return result
    return value


def context_summary(context):
    text = str(context)
    labels = re.findall(r"\[Source:\s*([^;\]]+);\s*page:\s*(\d+)\]", text)
    urls = re.findall(r"Source:\s*(https?://[^\s]+)", text)
    return {
        "characters": len(text), "content_sha256": sha(text),
        "document_labels": [{"file": file, "page": int(page)} for file, page in labels],
        "web_source_urls": list(dict.fromkeys(urls)),
        "raw_text_included": False,
    }


def trajectory_summary(result):
    return sanitize({
        k: [context_summary(context) for context in value] if k == "contexts" else value
        for k, value in result.items()
    })


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Completed local Output directory")
    parser.add_argument("destination", type=Path, help="Public package directory")
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Destination must be separate from the source artifacts.")
    low = source / "William_Matthew_Tyler_Project_III_Low"
    for directory in ("notebooks", "src", "reports", "evaluation", "evidence", "prompts", "data"):
        (destination / directory).mkdir(parents=True, exist_ok=True)

    # Results retain measured outcomes, but not the supplied reference-answer column.
    results = sanitize(json.loads((low / "evaluation_results.json").read_text(encoding="utf-8")))
    write_json(destination / "evaluation/evaluation_results.json", results)
    columns = list(results[0])
    csv_stream = io.StringIO(newline="")
    writer = csv.DictWriter(csv_stream, fieldnames=columns)
    writer.writeheader()
    for row in results:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                         for k, v in row.items()})
    (destination / "evaluation/evaluation_results.csv").write_text(csv_stream.getvalue(), encoding="utf-8")

    artifact_names = [
        "evaluation_scorecard.csv", "evaluation_by_category.csv",
        "evaluation_completed_scorecard.csv", "evaluation_denominators.csv",
        "evaluation_analysis.md", "evaluation_analysis.json", "evaluation_reflections.json",
        "judge_agreement_metrics.json", "judge_disagreements.csv", "judge_scored_disagreements.csv",
        "judge_validation_tests.json", "agent_failed_cases.json",
        "retrieval_diagnosis.md", "retrieval_diagnosis_evidence.json",
    ]
    for name in artifact_names:
        path = low / name
        target = destination / "evaluation" / name
        if path.suffix == ".json":
            write_json(target, sanitize(json.loads(path.read_text(encoding="utf-8"))))
        elif path.suffix == ".csv":
            rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
            fields = [f for f in rows[0] if f not in OMITTED_KEYS] if rows else []
            out = io.StringIO(newline="")
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: redact_string(row[key]) for key in fields})
            target.write_text(out.getvalue(), encoding="utf-8")
        else:
            target.write_text(redact_string(path.read_text(encoding="utf-8")), encoding="utf-8")

    # Curated failure log excludes supplied reference text while keeping actual diagnoses.
    failures = json.loads((destination / "evaluation/agent_failed_cases.json").read_text(encoding="utf-8"))
    failure_log = "# Saved benchmark failure diagnoses\n\n"
    for row in failures:
        failure_log += (f"## {row['id']} — {row['category']}\n\n"
                        f"Question: {row['question']}\n\n"
                        f"Recorded model answer: {row['answer']}\n\n"
                        f"Deterministic pass: {row['passed']}; judge: {row['judge_verdict']}; "
                        f"diagnosis: {row.get('diagnosis')}\n\n")
    (destination / "evaluation/failure_analysis.md").write_text(failure_log, encoding="utf-8")

    trajectories = json.loads((low / "evaluation_trajectories.json").read_text(encoding="utf-8"))
    for key in ("agent_results", "rag_results"):
        trajectories[key] = [trajectory_summary(result) for result in trajectories[key]]
    trajectories["public_edition"] = {"raw_contexts_omitted": True, "role": "trace summaries, not a resumable checkpoint"}
    write_json(destination / "evidence/evaluation_trajectory_summaries.json", sanitize(trajectories))

    for original, public in [
        ("Tesla_market_report_2026-10-05_reviewed.md", "Tesla_market_report_2026-10-05_reviewed.md"),
        ("Tesla_market_report_2026-10-05.md", "Tesla_market_report_2026-10-05_original_generated.md"),
        ("report_audit.md", "report_audit.md"), ("report_audit.json", "report_audit.json"),
    ]:
        path, target = low / original, destination / "reports" / public
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            write_json(target, sanitize(json.loads(text)))
        else:
            target.write_text(redact_string(text), encoding="utf-8")
    report_trace = json.loads((low / "Tesla_market_report_2026-10-05_trajectory.json").read_text(encoding="utf-8"))
    write_json(destination / "evidence/report_trajectory_summary.json", trajectory_summary(report_trace))

    for path, directory in [
        (source / "live_output_provenance.json", "evidence"),
        (low / "generation_retry_provenance.json", "evidence"),
        (low / "document_source_inventory.json", "evidence"),
        (source / "build_prompts.json", "prompts"),
        (source / "runtime_prompts.json", "prompts"),
    ]:
        write_json(destination / directory / path.name, sanitize(json.loads(path.read_text(encoding="utf-8"))))

    notebook_inventory = {}
    for variant in ("High", "Low"):
        name = f"William_Matthew_Tyler_Project_III_{variant}"
        original = nbformat.read(source / (name + ".ipynb"), as_version=4)
        public = nbformat.v4.new_notebook()
        public.metadata = {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": original.metadata.language_info,
            "portfolio": {
                "owner": "William Matthew Tyler", "edition": "public", "variant": variant,
                "canonical_live_variant": "Low", "independent_high_live_run": False,
                "outputs_cleared_for_publication": True,
                "original_code_source_sha256": code_hash(original),
            },
        }
        intro = f"""# Project III — {variant}-code public implementation

William Matthew Tyler's AI-assisted market competitor intelligence project.

This public edition keeps all 47 implementation code cells from the completed
course notebook. Course instructions, logos, private links, machine paths and
recorded cell outputs are omitted. The supplied reference dataset is private.
The measured run is preserved in the curated evidence files and the summary
below. Low-code is the canonical local run; High-code shares the same code and
run evidence. These are two presentation variants, not two independent trials.

See the repository README for attribution, credentials, data and reproduction.
Executing the code requires the separately supplied resources and live APIs.
"""
        public.cells = [nbformat.v4.new_markdown_cell(intro)]
        output_count = 0
        for cell in original.cells:
            if cell.cell_type != "code":
                continue
            index = int(cell.metadata["original_index"])
            if index in HEADINGS:
                public.cells.append(nbformat.v4.new_markdown_cell("## " + HEADINGS[index]))
            copied = copy.deepcopy(cell)
            copied.metadata = {"original_index": index}
            output_count += len(copied.outputs)
            copied.outputs = []
            copied.execution_count = None
            public.cells.append(copied)
        public.cells.append(nbformat.v4.new_markdown_cell("""## Recorded benchmark — October 5, 2026

| Measured outcome | Research agent | Naive PDF RAG |
| --- | ---: | ---: |
| Deterministic passes | 11 / 24 (45.8%) | 10 / 24 (41.7%) |
| Mean structured judge score | 0.7500 | 0.5625 |
| Mean latency | 5.72 s | 1.96 s |
| Mean tool calls | 1.54 | 1.00 |

All 48 answer records have valid judge verdicts. Deterministic/judge agreement
was 40 / 48 (83.3%). One transient authentication failure was retried; the other
47 answer roles and 47 original judge verdicts were reused. Successful wrong
answers were preserved. The separate source-audited report does not change
these benchmark outcomes. Latency is per-question generation time, not analyst
effort or end-to-end production throughput.
"""))
        for index in (141, 147, 152, 154, 156):
            public.cells.append(nbformat.v4.new_markdown_cell(redact_string(original.cells[index].source)))
        reviewed = (destination / "reports/Tesla_market_report_2026-10-05_reviewed.md").read_text(encoding="utf-8")
        public.cells.append(nbformat.v4.new_markdown_cell(
            "## Separately source-audited report\n\nThe following correction was prepared with AI-assisted source auditing. "
            "It is separate from the original generated report and the scored model answers.\n\n" + reviewed))
        assert code_hash(public) == code_hash(original), "Public export must preserve implementation source exactly"
        nbformat.validate(public)
        nbformat.write(public, destination / "notebooks" / (name + ".ipynb"))
        html, _ = HTMLExporter().from_notebook_node(public)
        (destination / "notebooks" / (name + ".html")).write_text(html, encoding="utf-8")
        code = "# Public notebook implementation; see README for data and credentials.\n\n"
        code += "\n\n".join(f"# %% Original implementation cell {c.metadata['original_index']}\n{c.source}"
                              for c in public.cells if c.cell_type == "code")
        (destination / "src" / (name + ".py")).write_text(code + "\n", encoding="utf-8")
        notebook_inventory[variant] = {
            "original_cell_count": len(original.cells), "public_cell_count": len(public.cells),
            "code_cell_count": sum(c.cell_type == "code" for c in public.cells),
            "original_output_blocks_cleared": output_count,
            "code_source_sha256": code_hash(public), "public_has_recorded_cell_outputs": False,
        }

    for name in ("requirements.txt", "config.example.json"):
        (destination / name).write_text((source / name).read_text(encoding="utf-8"), encoding="utf-8")
    write_json(destination / "evidence/public_edition_manifest.json", {
        "project_owner": "William Matthew Tyler", "recorded_run_date": "2026-10-05",
        "notebooks": notebook_inventory, "answer_records": len(results), "judge_verdicts": 48,
        "omitted": ["course PDFs", "golden_dataset.csv", "course instructions and logos",
                    "all recorded notebook outputs", "raw retrieval contexts/excerpts and raw checkpoint files",
                    "reference-answer fields", "private Colab IDs and screenshots", "credentials and preflight logs"],
        "preserved": ["all implementation code cells unchanged", "recorded model answers and metrics",
                      "tool arguments", "context hashes and source labels", "original generated report text",
                      "source-audited report", "retry and canonical-run provenance"],
        "original_artifacts_modified": False,
        "output_portability": "Personal machine paths in curated JSON/text evidence are replaced by bracketed local-path markers.",
    })
    print(json.dumps(notebook_inventory, indent=2))


if __name__ == "__main__":
    main()
