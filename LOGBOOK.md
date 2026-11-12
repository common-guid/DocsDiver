# Remove vendor-derived test docs
2026-11-11 10:38:11 | chore/remove-vendor-test-docs (platform_engineer)
Deleted docs-for-testing/api/ (12 files of third-party vendor API docs with the name replaced, 9 duplicates) from the public repo. The default test corpus is now the four synthetic files; history is unchanged.

---
# Record OpenRouter usage and cost in traces
2026-11-11 15:43:51 | feat/eval-p1-usage-cost (platform_engineer)
Eval phase P1: the OpenRouter adapter span now carries token usage, USD cost and a Langfuse-mapped model name, recorded once per call; the Langfuse exporter sends the v4 ingestion header.

---
# Add --docs-root and --output-dir (eval P2)
2026-11-12 14:00:00 | feat/eval-p2-path-overrides (platform_engineer)
main.py can point one run at any corpus and output directory without editing config.yaml, which the eval runner needs; an output directory inside the docs root is refused because the audit would index its own findings.

---
# P3 implementation blocked by A3 test failure
2026-11-12 14:48:29 | feat/eval-p3-run-manifest (platform_engineer)
Implemented the reviewed run-ID, span tagging, ledger, manifest and 17 tests; work remains uncommitted on feat/eval-p3-run-manifest. Disposable-copy baseline: 153 passed; mutation: 16 failed and 154 passed as expected; final: 169 passed and 1 failed (A3 ledger-empty assertion); stopped without workaround, live calls or PR.

---
# Complete P3 run manifests and per-run tracing
2026-11-12 14:56:56 | feat/eval-p3-run-manifest (platform_engineer)
Added run IDs, all-span session/tags, call provenance and atomic headless manifests following the reviewed P3 plan. Fresh disposable-copy verification passed 170 tests (153 + 17); mutation matched 16 failed/154 passed, and A3 uses the operator-approved actual-globals patch to handle module re-import isolation; no live check was run.

---
