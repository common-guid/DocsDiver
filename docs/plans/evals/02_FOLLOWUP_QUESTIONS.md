# Evals Follow-up Questions
Status: answered 2026-11-10; decisions below, consolidated in `03_EVAL_DESIGN_BRIEF.md` · Created 2026-11-10 · Follows `01_EVAL_BRAINSTORM.md` (§6 answers, §7 decisions)

These questions build on the Q1–Q5 answers. Answer inline (CriticMarkup is fine). Once F1–F6 are settled, the next documents are `03_EVAL_DESIGN_BRIEF.md` (the settled decisions in one place) and a prompt asking Fable 5.2 for the detailed eval design.
## Where we stand
- **Decision (Q1):** is a report good enough to hand over? The bar is finding ≥90% of the issues it should find, with accurate explanations, graded by a rubric.
  
- **Failure priorities (Q2):** missed issues, then invented issues, then inaccurate explanations. A finding must locate the issue and explain what it is and why it matters.
  
- **Corpus (Q3, Q5):** public documentation only. Hex's public docs (<https://learn.hex.tech/docs>) are the realistic candidate.
  
- **Budget (Q4):** at most $1.50 per run, provisional.
  
  - All 214 Langfuse generations since 2026-11-08 record $0 cost and 0 tokens, so the budget can't be checked yet. Capturing token usage and cost is a prerequisite; OpenRouter includes usage in its responses, but DocsDiver doesn't record it.
    
  - A full audit of `docs-for-testing/` is about 30–38 model calls, plus one Map Maker call per file. A Hex corpus of real size will cost much more.
    
## F1. Who writes the answer key, and is that time realistic?
"90% of the issues it should find" only means something against a list of those issues.

- **Synthetic corpora with planted issues:** the answer key is exact and cheap. Plant 10 issues and you know there are 10.
  
- **Hex:** someone has to read the docs and list the real issues. That's real expert time. Findings that aren't on the list also need a ruling: real and missing from the key, or invented.
  

**Proposal:** use both. Synthetic corpora carry the recall math; a small Hex slice checks realism. Does that split work, and roughly how much time can you give to writing and adjudicating answer keys?

> _Answer:_ {++Yeah, I think this is probably the right way to go instead of trying to identify real issues in real documentation. I think we should grab some real documentation like some hex and then plant certain issues that we are aware of and we can have an answer key for.++}{id="s1" by="user" at="2026-11-10T19:58:38.914Z"}
## F2. Which part of Hex, frozen how, stored where?
- **Size:** the full Hex docs are large, and corpus size is Strategic 2's problem. Proposal: freeze a dated snapshot of a security-relevant slice of about 20–40 pages, e.g. roles and permissions, sharing, workspace and API tokens, SSO/SCIM, data connections.
  
- **Storage:** keep the snapshot and its answer key **out of the public DocsDiver repo**, in the vault or a private repo, for two reasons:
  
  - Hex owns the copyright on the docs, so copying them into the repo means republishing them.
    
  - A list of security weaknesses in a real vendor's documentation is sensitive even when the docs themselves are public.
    

Which areas would you pick, and do you agree on storage?

> _Answer:_ {++Agreed, we keep them out of the repo. I think we should plant our own issues within a real documentation.++}{id="s2" by="user" at="2026-11-10T20:01:28.993Z"}
## F3. What counts as one issue?
Recall depends on how issues are counted: one "admin role is vague" finding could be scored as one item or three.

- **Issue types:** one per worker (permission gaps or ambiguity, broken or missing invariants, trust-boundary gaps), plus contradictions between documents.
  
- **Counting:** one key item per distinct claim a tester could act on.
  

Does that match how you think about it? Are any issue types missing, or out of scope?

> _Answer:_ {++Yeah, this is a tough one, but you're right there is probably too much overlap and we should probably reevaluate the prompts at some point, but What do you think about, instead of categorizing the issues, we just tag them? So it is entirely acceptable for one issue to have multiple tags. Just like you mentioned, the permission gap and ambiguity very well may have overlap on the example you provided, so why not just tag them with both? Do you have any objection to using tags? instead of distinct categories.++}{id="s3" by="user" at="2026-11-10T20:34:05.922Z"}
## F4. Does this rubric match how you'd grade?
- **Per finding, each scored 0, 1 or 2:**
  
  - _Located:_ right document and section.
    
  - _What:_ the issue is stated accurately.
    
  - _Why:_ the impact or risk reasoning is correct.
    
- **Invented:** a finding that matches no key item and is ruled not real.
  
- **Calibration:** you hand-grade about 10–20 findings once, so an LLM judge can be calibrated against your grades before it does the bulk of the scoring.
  

Would you grade differently, e.g. severity as a fourth dimension, or pass/fail instead of 0–2? Is hand-grading 10–20 findings acceptable?

> _Answer:_ {++I guess I'm okay with this. I haven't thought much about the specific scoring methodology, but if you recommend the 0-1-2 approach, then I guess I'm okay with that. Do you really think that this is the best approach?++}{id="s4" by="user" at="2026-11-10T20:36:15.620Z"}
## F5. Grade the final report or the worker outputs?
**Proposal:** apply the 90% gate to the final threat model (`reports/Security_Threat_Model.md`), since that's what gets handed over. Also score the worker artifacts, to show where an issue was lost: never found by a worker, or dropped during synthesis.

> _Answer:_ {++I think we should grade both, but if I have to pick one, I think that we grade the worker outputs against the answer key.++}{id="s5" by="user" at="2026-11-10T20:37:31.190Z"}
## F6. Is the 90% target per run or averaged?
With a 10-item key, 90% means at most one miss, and results vary between runs.

**Proposal:** ≥90% recall averaged over 3 runs, and no single run below 80%. Should invented issues have their own ceiling, e.g. at most one per report?

> _Answer:_ {++No, all issues should have the same. But yes, 90% recall is the minimum. No single run below 80%. I think that's reasonable, so yes, I agree with this.++}{id="s6" by="user" at="2026-11-10T20:38:19.869Z"}
## Decisions
Agreed in the answers above and in the 2026-11-10 chat follow-up. `03_EVAL_DESIGN_BRIEF.md` consolidates them.

| Date | Decision | Source |
| --- | --- | --- |
| 2026-11-10 | Corpus: take real public Hex docs and plant known issues, so the answer key is exact. | F1 |
| 2026-11-10 | Operator time for v0 answer keys: about 2 hours. The AI drafts planted issues and key entries; the operator reviews and approves them. | F1 (chat) |
| 2026-11-10 | Hex snapshot, answer key and run outputs are kept out of the public repo, in the vault at `projects/Doc_Analysis_Agent/evals/hex-v0/`. | F2 (chat) |
| 2026-11-10 | Hex v0 slice: roles and permissions, sharing, workspace (including workspace and API tokens). SSO/SCIM and data connections are out. | F2 (chat) |
| 2026-11-10 | Issues carry multiple tags from a fixed vocabulary instead of a single category. One key item is one distinct claim a tester could act on. | F3 |
| 2026-11-10 | Grading is binary on three checks per finding: Located, What, Why. Detection = Located + What; full credit = all three. | F4 (chat) |
| 2026-11-10 | Grade worker outputs first: overall recall over the union of workers, per-worker recall by tag. The final report is also graded, for synthesis retention. | F5 |
| 2026-11-10 | Gate: detection recall on planted issues ≥90% averaged over 3 runs, with no run below 80%. All issues weigh the same. | F6 |
| 2026-11-10 | Invented findings are measured and reported, with a threshold set after the baseline. Real issues in the docs that we didn't plant are never counted as invented: a clean-corpus run plus operator rulings records them as native. | F6 (chat) |
| 2026-11-10 | About 12 planted issues, spread across the tags, including some contradictions across pages. | chat |
| 2026-11-10 | First model under test: DeepSeek v4.1 Flash for every agent. It's weak but cheap; a stronger model is planned later. | chat |
