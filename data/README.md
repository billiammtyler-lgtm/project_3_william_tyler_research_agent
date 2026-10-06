# Resource boundary

The live implementation expects these exact filenames in `PROJECT3_DATA`:

| Filename | Source role / period label |
| --- | --- |
| `tsla-20260630.pdf` | Tesla Form 10-Q, quarter ended June 30, 2026 |
| `TSLA-Q2-2026-Update.pdf` | Tesla Q2 2026 Update deck |
| `tsla-20251231.pdf` | Tesla Form 10-K, FY2025 |
| `rivn-20260630.pdf` | Rivian Form 10-Q, quarter ended June 30, 2026 |
| `GlobalEVOutlook2026.pdf` | IEA Global EV Outlook 2026 |
| `golden_dataset.csv` | Course-provided 24-case evaluation dataset and reference answers |

The course resources are omitted from this repository. Obtain them through an
authorized course distribution, or use issuer/provider documents with the
correct provenance and period if adapting the project. Replacing documents or
the evaluation set produces a new corpus/benchmark and should not be represented
as reproduction of the recorded results.

Public starting points: [Tesla investor relations](https://ir.tesla.com/),
[Rivian investor relations](https://rivian.com/investors),
[IEA Global EV Outlook](https://www.iea.org/reports/global-ev-outlook-2026).
These links identify providers; they do not redistribute or authenticate the
exact supplied course files. `evidence/document_source_inventory.json` records
the names/page counts used in the saved run.

Reference answers are evaluator-only. The public results omit their full text;
all recorded model answers, verdicts and aggregate outcomes remain available.
Files placed in this directory are ignored by Git, except this README.
