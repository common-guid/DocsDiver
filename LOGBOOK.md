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
# Prepare Langfuse v4 platform instrumentation
2026-11-12 15:14:07 | ADK_master (platform_engineer)
Consolidated prompt and tracing clients onto one SDK-owned exporter, added propagated run-root I/O and explicit failure-safe flushing, and constrained the current SDK to >=5.2.0,<6. Validated 173 tests in a disposable copy, final focused regressions (9 passed), syntax and dependency checks; project evaluator, export and ingestion checks remain blocked in code-only mode.

---
# Add eval H1 corpus and key tools
2026-11-12 21:30:44 | feat/eval-h1-corpus-key (platform_engineer)
Added offline corpus verification, answer-key schema and interaction checks, and reproducible approved-edit builds with deterministic variant hashes. Added the synthetic Acme example and 101 tests; the disposable full suite passed 274 tests, compileall passed, and all six mutations were caught.

---
