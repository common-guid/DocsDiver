# Remove vendor-derived test docs
2026-11-11 10:38:11 | chore/remove-vendor-test-docs (platform_engineer)
Deleted docs-for-testing/api/ (12 files of third-party vendor API docs with the name replaced, 9 duplicates) from the public repo. The default test corpus is now the four synthetic files; history is unchanged.

---
# Record OpenRouter usage and cost in traces
2026-11-11 15:43:51 | feat/eval-p1-usage-cost (platform_engineer)
Eval phase P1: the OpenRouter adapter span now carries token usage, USD cost and a Langfuse-mapped model name, recorded once per call; the Langfuse exporter sends the v4 ingestion header.

---
