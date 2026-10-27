# Evidence acquisition and verification experiment

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
