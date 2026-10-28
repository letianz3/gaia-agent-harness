# Evidence acquisition and verification experiment

## Why the 82% increase had little benefit

Trace accounting locates the increase in recovery, not the initial solve:

| Chat tokens by boundary | Original 55% run | Previous 60% run | Difference |
|---|---:|---:|---:|
| Through the first critique | 294,891 | 285,895 | -8,996 |
| After the first critique | 51,783 | 345,378 | +293,595 |
| Total | 346,674 | 631,273 | +284,599 |

These are measured model-request usage totals split at the first critique event,
not a causal estimate from timing. The extra 280,717 input tokens account for
98.6% of the net increase; output increased only 3,882 tokens. Evidence, task
context and predecessor prose were copied through new plans, specialists,
synthesis and a second review. Planning tokens rose from 14,916 to 31,736;
synthesis from 10,726 to 68,311; critique from 39,043 to 87,061. Those latter
stage counts use adjacent trace events as attribution, not provider billing tags.

The previous 60% run had 29 UNCERTAIN review results, including 13 rejected
citations and 5 malformed JSON responses. Such reviewer failures were routed
through research as if they were missing facts. Exact quotations with inserted
ellipses, invalid escaping, and extra JSON brackets are output-contract failures;
another web search does not repair them. Only one challenger was marked selected,
and it was identical to its incumbent. Thus that run demonstrated **zero changed
answers accepted by recovery**. Its net one-question improvement came from the
initial answer sets (four gains offset by three regressions), not demonstrated
successful critic corrections. Tool changes, prompts and model/web variability
remain confounded.

The critic also repeated semantic mistakes (category membership) despite correct
arithmetic evidence, while withholding real wording repairs when factual support
was uncertain. Neither more calls nor literal citation matching addresses all
these failure modes. Memory compression never triggered in either run; one cache
hit cannot offset the repeated new prompts.

## Selective recovery revision

- Ask the critic for JSON output, short contiguous quotations, a proposed
  evidence-based correction or a concrete acquisition target. Keep quotation
  provenance validation; never accept invented/ellipsized quotations as exact.
- Treat parsing/citation failures as unusable reviews rather than a signal to
  restart the task. No automatic research without an actionable target.
- Repair explicit formatting violations with separate generation and independent
  equivalence review, preserving identity/values/membership. This verifies format,
  not underlying factual truth. Ambiguous expansions are rejected.
- Reuse a critic-proposed answer supported by existing evidence before new tools.
  When a fact is missing, use one targeted tool loop of at most three turns
  instead of another whole DAG. Preserve review before factual replacement.
- Bound evidence to 8,000 characters, shorten per-record arguments, merge by
  rebuilding one packet rather than concatenating old and new packets, and skip
  the second review if the candidate is unchanged. Bounded excerpts can still
  omit relevant passages; reduced cost alone is not a correctness guarantee.

The new policy passed 42 offline tests, including format/equivalence isolation,
rejecting broken reviewers without tool acquisition, bounded acquisition, and
conservative candidate selection. The original and intermediate results below
remain historical records; no task answers are hardcoded in the runtime.

### Measured result of selective recovery

Fresh full run `full_20261028T004401Z`: official **14/20 (70%)**, submitted at
2026-10-28T00:49:48Z (October 27 locally). Same gpt-4.1-mini and feature flags;
all 20 tasks completed, source snapshot matches the evaluated runtime.

| Metric | Previous expensive revision | Selective recovery |
|---|---:|---:|
| Official correct / 20 | 12 | 14 |
| Input tokens | 613,378 | 417,423 |
| Output tokens | 17,895 | 14,151 |
| Total chat tokens | 631,273 | 431,574 |
| Summed agent latency (seconds) | 432.256 | 341.705 |
| Model requests | 243 | 174 |
| Tool calls | 95 | 74 |
| Specialist executions | 58 | 35 |
| Full-DAG recovery replans | 13 | 0 |
| Targeted acquisitions | 0 | 5 |
| Existing-evidence repair proposals | 0 | 1 |
| Format/equivalence repairs accepted | 0 | 1 |
| Critic JSON parse failures | 5 | 0 |
| Citation failures | 13 | 7 |
| Memory compressions | 0 | 0 |

Chat tokens fell **31.63%**, latency **20.95%**. After-first-review tokens fell
from 345,378 to 90,574; through-first-review tokens rose from 285,895 to 341,000.
Format-only paths have no factual critique, so the comparator puts their usage
in the through-first-review bucket. Total usage is authoritative; the split is
an operational diagnostic, not a controlled attribution of every change.

Three gains (NASA award, city formatting, spreadsheet) were offset by one
regression (actor/character lookup). The accepted format repair fixed the city
answer. No changed factual challenger was accepted; the other gains arose in
initial solving/synthesis, so this single run does not prove that factual
verification became more accurate. It matches a historical 70% project score;
the leaderboard did not update its high score.

Six remaining misses concern bird-video coverage, chess image transcription,
botanical classification, recipe wording, actor lookup, and historical roster
retrieval. The actor regression explicitly reported missing evidence yet final
synthesis still proposed a name; selective acquisition did not verify it.
Citation errors and semantic agreement on a wrong classification remain open
problems. Cost is also still above the original 346,674-token reference, though
this run answered three more questions correctly. These development-set results
should be checked on held-out tasks before generalization claims.

## Scope and method

Compare two full 20-question runs with gpt-4.1-mini, temperature 0, and all harness
feature flags enabled. Each run has fresh web/tool caches and a source snapshot.
Use the official scorer once per completed answer set. Do not select answers
across runs or put benchmark labels into prompts or runtime code.

The initial run is `full_20261027T195531Z`, officially 11/20 (55%). Offline
comparison against the authorized GAIA validation metadata identifies nine
misses. Categories below describe observed failure mechanisms, not a proven
causal decomposition: retrieval and reasoning can fail together.

| Task prefix / topic | Evidence from original trace | Dominant issue |
|---|---|---|
| a1e91b78 / bird video | Sparse sampled frames treated as exhaustive coverage | Media capability / coverage |
| 9d191bce / video dialogue | Visual-only inspection; answer lacked audio support | Missing audio capability |
| cca530fc / chess | Cloud engine had no result; guessed move incompatible with extracted board | Engine gap plus unverified reasoning |
| 3cef3a44 / botanical categories | Worker introduced an exclusion absent from the question | Classification and coverage verification |
| 7bd855d8 / spreadsheet | File and totals were available; a food category was wrongly excluded | Reasoning, not spreadsheet access |
| 3f57289b / baseball statistic | Lookup delegated to analyst with no web tools; unsupported statistic asserted | Capability-aware routing / evidence fidelity |
| cf106601 / Olympics | Unsupported participant counts and tie-order reasoning | Source extraction / verification |
| a0c07678 / historical roster | Searches and official pages failed; purported roster facts still asserted | Retrieval plus unsupported synthesis |
| 5a0c1adf / historical nationality | Current page differed from historical framing; spelling mistaken for extinct country | Historical evidence and semantic verification |

## Changes

- Supply raw successful tool observations to synthesis, clearly separate worker
  conclusions, and prioritize recent direct observations over search snippets.
- Preserve evidence IDs and source arguments. Require exact quoted support for
  critic PASS; reject fabricated citations and search-only support. This proves
  quote provenance, not entailment or completeness. The model still must judge
  meaning, including whether a calculation's inputs are justified.
- Describe specialist tool capabilities to the planner. Require actual page
  retrieval, historical evidence where appropriate, and explicit inclusion /
  exclusion coverage. Never treat remembered source claims as retrieved facts.
- Add bounded search backend fallback, PDF page extraction, website challenge
  detection and redirect address validation.
- Increase video sampling from 18 to 48 frames and transcribe a separate audio
  stream for dialogue questions. Audio/video access can still fail; uniform
  sampling cannot prove the absence of brief events.
- Prefer an optional local Stockfish engine; validate legal FEN positions and
  label engine conclusions as conditional on correct visual transcription.

The first optimization run (`full_20261027T201325Z`) scored **11/20**, unchanged:
three gains (dialogue, baseball statistic, spreadsheet) and three regressions
(algebra, audio recipe wording, city identity). It used 431,566 chat tokens,
314.221 seconds summed agent latency, 80 tool calls and 2 replans. The trace
exposed an evidence-path defect: original audio transcripts were available to
the solver but absent from the critic's evidence packet. A successful Python
process with no printed result could also be treated as an observation.

The second revision retains original task/transcript evidence across replans,
excludes empty Python output, and allows one bounded evidence-acquisition
attempt for UNCERTAIN as well as FAIL. An uncertain challenger cannot replace
the incumbent. No runtime answers or benchmark-specific exceptions were added.

## Interpretation

Final run: `full_20261027T201910Z`, official score **12/20 (60%)** at
2026-10-27T20:26:26Z. All 20 completed. Runtime source hashes match the saved
snapshot. Validation: 36 tests passed after the runtime revision; two additional
bounded-acquisition policy cases passed afterward (38 test cases total).

| Metric | Original | First optimization | Final revision |
|---|---:|---:|---:|
| Official correct / 20 | 11 | 11 | 12 |
| Chat input tokens | 332,661 | 419,479 | 613,378 |
| Chat output tokens | 14,013 | 12,087 | 17,895 |
| Total chat tokens | 346,674 | 431,566 | 631,273 |
| Summed agent latency (seconds) | 399.213 | 314.221 | 432.256 |
| Tool calls | 90 | 80 | 95 |
| Specialist executions | 45 | 39 | 58 |
| Replans | 5 | 2 | 13 |
| Memory compressions | 0 | 0 | 0 |
| Model cache hits | 0 | 0 | 1 |

The final revision gained four tasks (dialogue, baseball statistic, Olympics,
historical nationality) and lost three (recipe wording, NASA award, city wording)
relative to the original. This is a net gain of one with **82.1% more chat tokens**
and **8.3% more agent latency**. The two optimization runs together used
1,062,839 chat tokens, excluding audio usage. This is not a cost-efficiency win
or a new historical project best.

Remaining failures include incomplete video coverage, image-to-board recognition,
category exclusions, historical roster retrieval, and overly conservative candidate
selection. In the recipe trace the critic inserted an ellipsis into its quotation;
the exact-quote validator correctly rejected that altered quotation, but also
prevented acceptance of a factually correct correction. For the award question,
the improved candidate had only snippet support. For the city question, a format
repair was rejected because factual verification remained uncertain. These are
limitations of the current evidence policy: quoting a real source does not prove
semantic correctness, while requiring a new factual PASS for a format-only repair
can retain a known formatting error. The spreadsheet example also still excludes
a legitimate category despite correct numeric extraction, so the model's critic
can agree with the solver's semantic mistake.

Next controlled work should separate deterministic formatting repairs from factual
replacement, require short contiguous source quotations, and target semantic
coverage checks. Evaluate these on held-out questions before claiming general
improvement. The two evaluated revisions are preserved; no best-of-run answer
mixing was used.

This is a same-model engineering comparison, not an isolated architecture
ablation. Tool and prompt changes are bundled; web content and model responses
can vary. Twenty known questions have high variance and development-set bias.
Improvement on this set does not establish generalization. Memory compression
and caching only affect a run if their triggers are reached.

Raw task-level records remain local under `.runs/`. Public reports contain
aggregate metrics and failure descriptions, not answer keys. Chat-token counts
exclude audio transcription usage; wall-clock run time and summed agent latency
are different quantities. An unset price is unknown cost, not zero cost.
