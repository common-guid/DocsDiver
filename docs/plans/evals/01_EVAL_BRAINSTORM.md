# Evals Brainstorm (Strategic Feature 1)

Status: brainstorming, not a plan · Started 2026-11-10 · Roadmap: `ROADMAP.md` §3 Strategic Feature 1, release 0.4

Working notes for designing DocsDiver's quality evaluation. Answer the questions in §6 inline (CriticMarkup is fine); settled answers move to §7. Later documents in this directory are numbered `02_…`, `03_…`.

## 1. Current state (observed 2026-11-10)

- **Real runs exist in Langfuse.** Generation and tool traces from OpenRouter runs, most recently 2026-11-10 02:27 UTC. These are raw material for reviewing real outputs.
- **Langfuse has no datasets yet.**
- **The test corpus gives away the answers.** `docs-for-testing/` is about 220 words, and the flaws are labelled in the text, e.g. `roles.md`: *"(Intentional flaw: Vagueness about what admin can do…)"*. A model that reports the flaw may just be reading the label. An eval corpus must remove the labels and keep the answer key in a separate file.
- **The reports are free-form Markdown.** Scoring them takes a person or an LLM judge. This is why the Roadmap ties evals to structured findings (`sdaa/src/schemas/findings.py`).

## 2. What decision should the first eval drive?

Start from the decision the eval informs. Candidates:

1. **"Is a prompt or model change better or worse?"** Compare versions while tuning agents. The most common and most reusable.
2. **"Is a report good enough to hand to a client?"** An absolute quality bar; needs agreed thresholds.
3. **"Which model should each agent use?"** Cost against quality.

For a batch tool with no live users, start **offline**: run fixed corpora and compare outputs. Online scoring of real runs can come later.

## 3. What "good" means: candidate dimensions

Roughly in priority order:

| Dimension | Question | Checkable how? |
|---|---|---|
| **Recall** | Did it find the issues we know are there? | Answer key of known issues; matching is the hard part |
| **Grounding** | Is each claim backed by text that actually exists in the docs? | Deterministic once findings carry citations |
| **Evidence status** | Does it separate "docs say X", "docs contradict each other" and "docs are silent"? | Judge or human |
| **Precision** | How many findings are noise or invented? | Human or judge |
| **Synthesis fidelity** | Does the final report keep the worker findings without dropping or inventing any? | Comparison against the worker artifacts |
| **Robustness** | Does a planted "ignore previous instructions" line in a doc change behaviour? | Planted adversarial docs |
| **Operational** | Cost, tokens, latency, completion rate | Already in the traces |

On evidence status: absence of documentation must not be reported as proof that the control is missing in the implementation.

**The hardest technical problem is matching:** deciding whether a free-text finding counts as an expected one.
- Keyword matching is brittle.
- An LLM judge needs calibrating against human labels.
- Human review doesn't scale.

Findings that carry file, line range and category make matching close to mechanical. That's the strongest argument for doing the schema work early.

## 4. Prerequisites

### Must have before the numbers mean anything

- **A corpus with the flaw labels removed, plus a human-written answer key.** Expected findings come from a security expert (the user); AI-generated answers are not ground truth. Start small, about 5–12 high-signal items. Seed facts from the Roadmap: the authentication roles and the "paid invoices can't be changed" invariant.
- **Every eval run records exactly what it ran:** model per agent, prompt *versions* (not just the movable `production` label), corpus hash, code commit. Otherwise results can't be reproduced or compared.
- **A way to run the eval without editing tracked config.** `docs_root`/`output_dir` come only from `sdaa/config/config.yaml` today. The Roadmap puts `--docs-root`/`--output-dir` in Strategic 3, but evals need them sooner. The change is small.
- **Repeat runs.** LLM output varies, so one run per configuration says little. Plan on at least 3 runs and report the spread, and set a cost budget per eval run.

### Decide early

- **Confidentiality.** `config.yaml` has a commented-out engagement corpus, and traces send raw prompts and documents to Langfuse cloud. Can client documents ever be used in an eval or go into Langfuse? Proposed default: no; evals use synthetic or public docs only.
- **Where eval files live.** The Roadmap says `evals/` in the repo, which stays the source of truth. Langfuse datasets/experiments could be where runs are compared. A dataset item would likely be one corpus, or one (corpus, agent) pair, rather than a single question.

### Not blocking

- **Tactical 2 (local prompt fallbacks)** matters for an offline CI gate. The prompts in Langfuse work today, so it doesn't block a live quality baseline.

## 5. Proposed starting sequence

1. **Review real outputs before defining metrics.** Use Langfuse's error-analysis method: the user reads generations from real runs and writes down in plain words what went wrong; an annotation queue can be set up for this. This grounds the issue categories in real failures.
2. **Baseline the current Markdown output.** Run a small corpus with the labels removed, score it against the answer key, and record the result. Without it, we can't tell whether the schema migration improves quality or only changes its shape.
3. **Then schema and citations.** With structured findings, grounding becomes deterministic and recall matching becomes mostly mechanical.

Keep two kinds of eval apart:
- **Replaying recorded responses offline** catches code regressions. It says nothing about model quality.
- **Live runs** measure quality. They cost money and must be opt-in.

## 6. Open questions

Q1 and Q2 shape everything else.

**Q1. Which decision from §2 matters most right now?**
> _Answer:_

**Q2. When you've read DocsDiver's reports so far, what made you wince?** (Missed issues, invented ones, vague severity, bloat, other?)
> _Answer:_

**Q3. Is there a real-world documentation set (public or yours) you'd trust as a realistic test, or is synthetic the only option?**
> _Answer:_

**Q4. Roughly what spend per eval run is acceptable?**
> _Answer:_

**Q5. Confidentiality: may client/engagement documents ever be used in evals or sent to Langfuse?** (Proposed default: no.)
> _Answer:_

## 7. Decisions log

| Date | Decision | Source |
|---|---|---|
| | | |

## 8. Session notes

### 2026-11-10: initial brainstorm
- Created this document from the first brainstorming discussion.
- Langfuse CLI and skill verified working against the project (read-only checks only).

## References

- `ROADMAP.md` §3 Strategic Feature 1 and §4 release 0.4
- Langfuse evaluation guidance: <https://langfuse.com/academy/evaluate/choosing-what-to-evaluate>, datasets <https://langfuse.com/academy/datasets>, error analysis <https://langfuse.com/guides/cookbook/error-analysis-llm-applications.md>
- Index of Langfuse docs: `docs/llms-txt/langfuse-llms.txt`
