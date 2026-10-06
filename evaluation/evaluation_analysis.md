# Evaluation analysis — canonical checkpoint-completed benchmark

**Interpretation of the measured scorecard**

The agent passed 11/24 questions (45.8%) versus 10/24 (41.7%) for naive RAG, and its mean judge score was 0.750 versus 0.562. The largest gains were web-current questions (3/3 versus 0/3 deterministic passes) and hybrid questions (2/3 versus 0/3), while naive RAG did better on PDF-only factual cases (7/12 versus the agent's 5/12). The agent used 1.54 calls per question versus 1.00, and averaged 5.72s versus 1.96s; the benchmark includes one documented retry of a transient authentication failure, with the initial attempt preserved.

**Failure analysis from the saved live run**

| Case | Symptom | Confirmed root cause | Targeted fix |
| --- | --- | --- | --- |
| `gold_04`, Q2 free cash flow | Reported positive $5,762 million instead of negative $1,092 million | The retrieved Update p.31 chunk contained the TTM row, while the quarterly row was outside the returned passage; synthesis used the wrong period | Retrieve the quarterly Financial Summary/reconciliation with row and column headers; reject TTM for a quarterly question |
| `gold_05`, storage deployed | Reported 22.3 GWh instead of Q2's 13.5 GWh | Three searches omitted the quarterly row and returned 10-Q p.35 saying 22.3 GWh **through the second quarter**, which the answer relabeled as Q2 alone | Target the Update p.5 Operational Summary and preserve period headers; validate cumulative versus three-month figures |
| `gold_07`, FY2025 energy gross profit | Said the gross-profit figure was not directly disclosed | One query retrieved 29.8% gross-margin discussion on 10-K p.66 without $3,802 million, although the gross-profit table exists on pp.64/145 | Require a second distinct segment-table search before a refusal and improve table chunk boundaries |
| `gold_02`, total GAAP gross margin; **scored disagreement** | Deterministic fail, judge `correct`, despite an accurate 16.8% answer | The answer cites the valid 10-Q p.39; the file whitelist expects only the Update deck, and the evidence string has `16.8 %` rather than `16.8%` | Keep the rubric score but add normalized evidence checks and independent validation of any valid supplied file/page |

For `gold_02`, I agree with the judge about the requested figure: independent extraction of the cited 10-Q p.39 confirms the Q2 total gross margin. Its automatic “retrieval miss” label is therefore a lexical/file-check limitation, not evidence that the figure was absent from the passage. The hard errors in `gold_04`–`gold_07` are supported by their saved queries, contexts, answers and judge reasoning; the source audit identifies the correct figures independently.

The judge also needs review. In `gold_18`, it claimed that an answer confirmed 13.5 GWh and lacked URLs, although the text omitted 13.5 and contained URLs; in `gold_20`, it accepted October-dated articles for a September-news question without establishing September event dates. These findings leave the raw judge scores unchanged and show why a strong model's verdict is not an independent fact check. The original generated report and its period/citation mistakes are retained separately from the reviewed final report.


**Key takeaways**

- The manual LangGraph agent adds useful source coverage: web-current and hybrid deterministic passes were 3/3 and 2/3, compared with 0/3 in both categories for document-only RAG. Overall judge scores were 0.750 versus 0.562; these are outcomes on 24 supplied questions, not a general accuracy guarantee.
- Tool access does not guarantee better PDF retrieval. The gold figure appeared lexically in 50.0% of the agent's numeric trajectories versus 61.1% for naive RAG. FCF, storage deployment and gross-profit failures show that query choice, table boundaries and period interpretation matter as much as the model.
- Deterministic and scored-judge decisions agreed on 40/48 answers (83.3%), but `gold_02` exposes strict-file/spacing false negatives and `gold_18`/`gold_20` expose judge reasoning/date weaknesses. The source audit and human review remain necessary.
- The checkpoint recovered one transient runtime authentication failure while preserving the other 47 completed roles. Initial results, the retry trajectory, and reused-versus-fresh judge provenance are retained; wrong but successfully generated answers were not silently repaired.

**Expected business impact for Allied FinServ**

- **Analyst effort:** the agent produced a source-backed first pass in 5.72s per benchmark question on average, compared with 1.96s for naive RAG. This measures machine response time; analyst time saved, review time, ROI and production turnaround were not measured.
- **Reviewability:** saved tool arguments, returned passages, file/page labels, scorecards and the preserved original report let an analyst trace and correct a claim. The reviewed report demonstrates the intended review workflow, while the original errors remain visible.
- **Freshness:** the agent can reach dated web sources that document-only RAG cannot; all three web-current cases passed the prescribed checks. The September/October mismatch in `gold_20` means dates still require validation before use in a client-facing brief.
- **Coverage:** the agent combined company filings with competitor web evidence in two of three hybrid cases, whereas the baseline passed none. This could broaden competitive monitoring; consistent company, period and BEV-versus-total-sales definitions still require analyst oversight.

**Prioritized workflow improvements**

1. Preserve complete financial table headers and rows, suppress title-only chunks, and add targeted quarterly/segment-table queries. This addresses the observed FCF TTM mix-up, H1 storage substitution and missed $3,802 million gross-profit row.
2. Validate each numeric claim against its exact cited page, including company, sign, unit and reporting period. Check dated web items against the requested time window and prefer primary releases; this would catch the report's citation errors and the September/October issue.
3. Retain the assessed deterministic metrics, but add normalized whitespace, supported-source/page and refusal-semantic checks. Calibrate the judge with the actual `gold_02`, `gold_18` and `gold_20` discrepancies rather than relying only on two period-swap examples.
4. Keep bounded transient-error recovery, configuration fingerprints, separate runtime/judge status counts and explicit cache provenance. The one recovered authentication failure shows the value of this control, while preserving first-pass content failures prevents misleading improvement claims.
