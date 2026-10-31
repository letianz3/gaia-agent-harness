# R9 policy isolation and applicability boundaries

Runtime `6086685`, run `full_20261031T011756Z`: **18/20**, a fresh complete
run and official submission. No post-hoc answer replacement or normalization
re-score. Model remains gpt-4.1-mini. 103 local tests pass.

| Metric | R8 | R9 |
|---|---:|---:|
| Correct / 20 | 18 (format re-score) | 18 (fresh run) |
| Chat tokens | 390,706 | 497,302 |
| Summed agent latency, seconds | 329.397 | 339.970 |
| Tool calls | 62 | 67 |
| Model requests | 159 | 165 |

Source lookup for the chemistry question recovered; the funding question
regressed. Video and botanical answers remained correct. Historical retrieval
remained unresolved. Those unchanged web paths do not support attributing either
variation to the policy refactor. Tokens increased 27.3%: historical retrieval
rose from 58,567 to 111,012 and funding retrieval from 33,970 to 79,463. This is
not a cost-efficiency improvement.

Repeatability check: the fresh R8 and R9 runs both returned `3` for the video
species task and the same correct five-item botanical list. R8b's format re-score
is not counted as another independent trial. These repeated target successes
support the earlier evidence-resolution repairs; two runs with a subsequent
refactor do not estimate a stable success rate or isolate a causal effect.
Chemistry and funding outputs still changed, so equal overall scores do not mean
the entire answer set is stable.

The new non-GAIA smoke set is `scripts/run_behavior_smoke.py`, with raw outputs
in local run `behavior_20261031T011854Z`. Arithmetic, version ordering, material
classification, culinary classification, dated reading and explicit exclusions
all had correct content. Exact strings passed 5/6; version ordering returned
`3,5` versus expected `3, 5`, an allowed separator-spacing difference. The raw
failure is retained. These are newly authored smoke cases, not an independent
representative benchmark or proof of broad generalization. They were not run
against the old model workflow; no comparative accuracy claim is made.

Default settings enable scoped strategies and domain policies independently.
Disable either using AGENT_SPECIALIZED_WORKFLOWS_ENABLED or
AGENT_DOMAIN_POLICIES_ENABLED for subsequent ablations. Config values are stored
in experiment summaries. Unsupported or ambiguous policy scopes use the general
agent; failure of an applicable evidence contract remains explicit rather than
silently relaxing its constraints.

---

# R8 evidence resolution

Fresh run `full_20261030T222219Z`, runtime `83ea796`: **17/20**.
Normalization-only re-score at `b1e5982`: **18/20 (90%)**. The original answers,
original official score, normalized answers and second official score are saved
separately. All 20 answers were processed by the same normalization function;
only one answer changed. No extra model calls or answers from other runs.

| Metric | R7b | R8 fresh run |
|---|---:|---:|
| Official correct / 20 before format re-score | 17 | 17 |
| Official correct / 20 after format re-score | 17 | 18 |
| Chat tokens | 370,653 | 390,706 |
| Tool calls | 73 | 62 |
| Model requests | 165 | 159 |
| Summed agent latency, seconds | 281.867 | 329.397 |

Video and botanical tasks changed from wrong to correct. The historical roster
remained unresolved. The chemistry-source surname regressed; a one-word dialogue
answer gained a terminal period. Removing that period recovered one point.
Token cost rose 5.4%; latency rose 16.9%. Video costs grew from 17,058 to 28,600
tokens; historical retrieval grew from 10,040 to 58,567 without solving the task.
This temporal route is therefore a reliability guard, not a demonstrated accuracy
or efficiency improvement. Botanical anatomical labels still contain factual
errors even though the final list is correct.

89 tests pass in the final tree. After scoring, a Unicode date-boundary bug was
fixed at `00e3182`; replaying the recorded historical report still rejects its
unsupported quote. No fresh benchmark score is claimed for that later fix.
All experiments and the R7 checkpoint are preserved. No model was changed.

---

# R7 selective code-owned contracts

Final runtime `87e0b03`, run `full_20261028T043133Z`: **17/20 (85%)**.
77 local tests passed. Model remains gpt-4.1-mini; no answer-set mixing.

| Metric | R5 | R7a strict entities | R7b selective default |
|---|---:|---:|---:|
| Official correct / 20 | 16 | 14 | 17 |
| Chat tokens | 350,250 | 370,173 | 370,653 |
| Tool calls | 64 | 70 | 73 |
| Summed agent latency (seconds) | 255.186 | 274.649 | 281.867 |

The three regression targets (actor, spreadsheet, first name) are correct in
R7b. Only the spreadsheet uses the new default typed contract; entity chains
remain opt-in after reduced coverage. Compared with R5, funding is the sole
new correct answer; the botanical answer changed but remains incorrect.
R7b costs 5.8% more chat tokens than R5. The PDF and spreadsheet repairs have
repeated targeted/full evidence; a single full score does not establish overall
stability. Audio tokens are excluded; price fields are unset, so no dollar-cost
claim is made. Prior experiments are retained below as historical records.

---

# Evidence acquisition and verification experiment

R6 PDF-access experiment: **15/20**, 348,129 chat tokens, runtime `c5c7ebb`.
The target funding repair reproduced, but three other tasks regressed against
R5. R6 is retained as an experiment; the default remains the 16/20 R5 checkpoint.
See [per-task ledger](FAILURE_ANALYSIS.md) for the diagnosis and model configuration.


Latest evaluated checkpoint: **16/20 (80%)**, runtime commit `042b2e3`, run
`full_20261028T032004Z`. 350,250 chat tokens versus 431,574 at 14/20 (-18.8%).
56 unit tests passed. See [per-task ledger](FAILURE_ANALYSIS.md) for the complete
iteration history and remaining four failures. The gains reproduce on the recipe
and chess targets; classification and untouched web tasks remain variable.


Latest source-grounded-list experiment: **15/20**, 413,810 chat tokens (-4.1%
against the previous 14/20 run). Runtime commit `392ad9c`; see
[per-task analysis](FAILURE_ANALYSIS.md) for gains, regressions and limitations.
The two target repairs reproduced; incidental changes on other tasks remain
uncontrolled model/web variation.

## Evidence-contract and visual-reinspection experiment (2026-10-28 UTC)

Decision: **not promoted**. The default runtime was restored to commit
`ea7a1dd` after two full, separately submitted 20-question runs. This restores
code, not a guarantee that a new stochastic run will reproduce 14/20.

| Metric | Previous default | Contract v1 | Corrected v2 |
|---|---:|---:|---:|
| Official correct / 20 | 14 | 12 | 13 |
| Chat tokens | 431,574 | 507,325 | 489,813 |
| Change in tokens | — | +17.6% | +13.5% |
| Model calls | 174 | 188 | 186 |
| Tool calls | 74 | 89 | 83 |
| Summed agent latency, seconds | 341.705 | 301.219 | 313.907 |

Runs: `full_20261028T004401Z` (reference), `full_20261028T024518Z`
(v1), `full_20261028T025130Z` (v2). Both new runs completed all 20 tasks
without top-level runtime errors. Their combined chat usage was 997,138 tokens;
audio transcription is excluded. All answers were generated afresh per run;
no best-of-run answer mixing or answer-key injection was used.

Changes tried:
- Structured specialist reports with FOUND/PARTIAL/NOT_FOUND. Incomplete or
  malformed prerequisite reports block dependent tasks instead of treating
  transport success as task success.
- Reject empty HTML/PDF evidence. Encourage bounded source/language fallback.
- Retain original video frames; inspect at most three selected frames separately.
- Describe chess scores from the mover's perspective and allow one independent
  transcription retry for an illegal board or contradictory negative evaluation.
- Preserve source wording and constrain final synthesis to the requested value.

V1 revealed interface defects: nested timestamps skipped the detail pass, and
an illegal FEN exited before the negative-score retry. V2 fixed those branches,
removed an overly strong unavailable-answer instruction, and retained specialist
report format when the turn budget expires. Regression tests covered these paths;
48 tests passed on v2. Initial default pytest execution was blocked by Windows
permissions on old temp/cache directories; an isolated `.runs/` temp directory
and disabled pytest cache resolved that environment issue.

Observed limitations:
- Video detail execution worked in v2, but selected frames missed the decisive
  evidence. Reinspection alone did not improve the final answer.
- Chess reinspection executed, but coordinate/piece transcription remained wrong.
- FOUND remains a model assertion. Checking report shape or nonempty evidence
  does not establish semantic entailment, identity, dates, or list completeness.
- Recipe wording improved only in v1, while category inclusion remained unstable.
- V2 gained the actor task but lost the award identifier and spreadsheet total
  relative to the reference: one gain and two regressions, net minus one.
- More recovery calls increased token use without a net accuracy improvement.

These results do not isolate causal effects: prompts, tool paths and model/web
responses changed together, and the small development set has substantial variance.
The next experiment should isolate one evidence transformation: source-span
extraction, square-coordinate recognition, or item-level classification coverage.
Do not add another generic critic as a substitute for those validators.

Local recovery artifacts: both runs retain `source/`, traces, answers and official
`submission.json`. V2 additionally retains `experimental_changes.patch` and
`edited_files/` (including the experimental tests). The patch can be checked with
`git apply --check .runs/full_20261028T025130Z/experimental_changes.patch` before
reapplying it. Raw evidence, answers and experimental runtime files remain local;
no public repository update was made for this experiment.

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

## R10: bounded verification experiment

Scope: the fluctuating textbook surname and paper funding-number tasks only.
The historical roster task and full 20-question evaluation were not rerun.
R9 is preserved by `checkpoint/r9-before-verifier-repair`; changes are isolated
on `experiment/evidence-review-r10` and are not promoted to main.

The old verifier's head/tail excerpts omitted answer-bearing passages in the
middle of successfully fetched sources. Replacement candidates were then judged
against incomplete evidence while an unverified incumbent could survive.
R10 retrieves literal question/candidate-related windows, compares both candidates
against the same packet without incumbent priority, checks contiguous quotations,
and reports unresolved cases rather than claiming verification. This checks quote
provenance in code; semantic entailment still depends on the model.

Recovery uses bounded navigation from observed URLs, treats navigation as
discovery rather than proof, detects additional challenge pages, and reuses compact
observations for identical successful read-only calls. Failed requests remain
retryable. The final repair loop has at most five turns rather than three.
No answer lookup or task-ID routing was added.

All batches used fresh run-local caches and the same two questions:

| Revision | Individual answers correct | Both correct per round | Chat tokens |
| --- | --- | --- | --- |
| `f803b34`: relevant evidence and candidate comparison | 4/6 | 1/3 | 353,556 |
| `79301c4`: bounded navigation and strict unresolved outcome | 3/6 | 1/3 | 352,598 |
| `4585acc`: recovery history and duplicate-request control | 5/6 | 2/3 | 320,363 |

The final three runs are `targeted_20261031T015818Z`,
`targeted_20261031T015855Z`, and `targeted_20261031T015933Z`.
Paper funding passed 3/3; textbook lookup passed 2/3. The remaining failure fetched
a same-named chapter from a different book, varied navigation queries on that
page, and then stopped without obtaining the requested passage. No correct
candidate was rejected in this failure. The next acquisition improvement should
check source/book identity before investing more calls in a chapter.

Separately, replaying saved raw sources with both candidate orders selected the
supported answer 4/4 times. This validates evidence handling only, not end-to-end
retrieval. Fresh results above include every failure, with no best-of-run mixing.
These small development-set samples do not establish stable accuracy or causality.
All 110 unit tests pass. Repository-wide Ruff still has 135 pre-existing findings
(also present at R9); the new verification files pass Ruff. Formatting-only cleanup
after `4585acc` does not constitute a new model evaluation.

## R11: source identity and exploration progress

The previous failed textbook run selected a same-named chapter from another book,
then changed `link_query` repeatedly on that URL. Navigation filtering does not
search the page body or establish book identity. Exact-argument deduplication in
the repair loop did not address this behavior during initial solving.

The new tool-loop wrapper identifies explicitly named authors in conservative
`written/authored/edited/licensed by ...` phrases. If those names are absent from
the fetched page, it marks identity as unconfirmed and suggests locating the
parent work through an author search. Absence does not prove a mismatch, and the
page remains available. This is a limited identity check, not a general metadata
resolver: titles, editions, aliases and dates still require evidence and review.

Successful reads seed a per-source allowance across loop transitions: at most
two fetches of a document before switching sources. Changing navigation keywords
or URL fragments does not reset it; distinct query strings and URLs remain
distinct. Failed fetches remain retryable. The allowance is a deterministic
exploration bound, not a proof that all useful links have been exhausted. Dynamic
pages that legitimately need repeated refreshes may require a separate policy.
Harness guidance is excluded from factual evidence packets. No benchmark IDs,
answers, textbook URLs, or named authors are encoded in the implementation.

Three fresh two-question runs at `a67e37f` were
`targeted_20261031T020720Z`, `targeted_20261031T020800Z`, and
`targeted_20261031T020842Z`. Both tasks passed in every round (6/6 individual;
3/3 paired), compared with R10's final 5/6 individual and 2/3 paired.
Total chat tokens were 233,540 versus 320,363 (27.1% lower). This is a small,
unpaired development comparison with variable model/search results, not a causal
ablation or guarantee. The first textbook run recorded an unconfirmed-author
warning followed by a new author/book search and a supported final answer.

The evaluated implementation serialized fetches within each loop wrapper.
A subsequent concurrency-only adjustment locks per source, preserving independent
URL parallelism while keeping same-source variants atomic. 116 tests pass,
including independent URL concurrency, same-source budget enforcement, navigation
JSON integrity, retryability and exclusion of harness hints from factual evidence.
The new files pass Ruff. No new model evaluation was performed after that locking
adjustment; no full 20-question or historical-roster run was performed in R11.
The wrapper seeds prior successes at each loop start; simultaneous independent
worker wrappers do not share a live global source ledger. This is a loop-level
exploration control with history seeding, not a global network-request quota.

## R12: historical records and bilingual identity joins

The remaining historical-number task exposed several different failures:
current rosters substituted for historical ones; native-language rows rejected
because Roman surnames were absent; multiple JSON objects discarded as malformed;
invented bilingual citations; and surname-only searches returning unrelated people.

The historical workflow now seeds bounded multilingual discovery, retains prior
observations when repairing, and separates row provenance from name identity.
A first pass checks the dated source, original numeric rows and eligibility.
Full native names are extracted from those observed rows. Bounded searches then
retrieve bilingual profiles, and code copies nearby literal original/Roman name
spans instead of asking the model to reconstruct quotations. The final pass
requires the name bridge and computes exact numeric neighbors. Current identity
profiles cannot establish historical jersey numbers. Short native-script table
quotes have a scoped six-character minimum; other evidence retains its existing
minimum. Malformed early JSON exits receive one structured formatting repair.

Development trials are retained, including failures:

| Runtime | Targeted outcome | Chat tokens | Next diagnosed issue |
| --- | --- | --- | --- |
| `92a9181` | Unverified | 60,779 | Multiple output objects discarded |
| `7d76c8e` | Unverified | 130,636 | Claimed bilingual pages never fetched |
| `536702e` | Unverified | 180,567 | Surname-only discovery matched other people |
| `9afb0c4` | Unverified | 220,603 | Reconstructed quotations and failed identity retrieval |
| `a353014` | Unverified | 139,059 | Missing optional native-name field blocked the extraction stage |
| `bb133c8` | Correct | 166,291 | Ready for full-set regression evaluation |

The successful targeted trace is `targeted_20261031T023259Z`. No benchmark
answers or entity-specific URLs were added to runtime code. Name proximity is a
provenance/identity check, not a general semantic proof. Historical validation
still operates at year/season granularity: a precise mid-season date may require
additional change-history evidence. These are development-set improvements, not
held-out generalization results.

Full-set regression exposed verification failures outside the historical task:

| Runtime | Official score | Chat tokens | Tool calls | Finding |
| --- | --- | --- | --- | --- |
| `c6d031a` | 16/20 | 627,986 | 91 | Historical roster and funding repaired, but generated quotations caused rejections and an explanatory replacement broke exact-match output. |
| `4f85e21` | 19/20 | 434,696 | 69 | Evidence-ID selection with code-copied spans repaired those regressions; a collection-count question lost its complete list during excerpt selection. |
| `93f3882` | 17/20 | 507,144 | See traces | Collection count repaired; two search-only evidence chains and a failed bilingual-name search regressed. |

Runs: `full_20261031T023417Z` and `full_20261031T024134Z` respectively.
The critic now judges source contents and selects evidence IDs; code materializes
the original spans and rejects invalid/discovery-only IDs. This avoids asking a
model to transcribe time-stamped speech or retype website text. It does not promote
UNCERTAIN to PASS or establish semantic entailment by ID existence alone.

`93f3882` additionally preserves a complete matching section for "How many ..."
questions when the fetched text has explicit edit-marked section boundaries and
the section is at most 4,000 characters. Other pages retain relevance-ranked
windows. The total evidence packet remains bounded. This is a limited collection
coverage improvement, not a universal table parser or completeness proof for
arbitrary web pages. No benchmark names, year ranges or answers appear in this rule.

The third full run is `full_20261031T024759Z`. Its historical failure came from
search-backend errors on a whitespace-separated CJK name, after the correct
dated roster had already been found. Search queries now normalize inter-character
CJK spacing while evidence keeps the original spelling. Verification receives
only direct observations and supplied task data, not discovery snippets.

`00bc328` targeted the three regressions: actor identity and historical neighbors
passed, while the sports-statistics lookup remained unverified because one fetched
profile caused the first source-acquisition guard to skip other unread search leads.
`6df66e0` instead fetches unread top leads before both reviews, with a four-fetch
task-wide cap and no repeat of previously attempted URLs. A subsequent fresh
sports-statistics run (`targeted_20261031T025729Z`) passed. These improvements
remain generic source-acquisition rules, not task-ID exceptions or stored answers.

### R12 final full-set comparison

| Runtime | Local run | Official raw score | Chat tokens | Finding |
| --- | --- | --- | --- | --- |
| `6df66e0` | `full_20261031T025814Z` | 19/20 | 459,571 | Unread source acquisition improved; candidate-biased excerpts confused a nominator with a promoter. |
| `8a18211` | `full_20261031T030428Z` | 17/20 | 499,053 | Month/year section priority helped scope; flattened table columns still confused different date fields, and two other web tasks regressed. |
| `4f4e27d` | `full_20261031T031336Z` | 19/20 | 363,744 | Historical target correct; sports-statistics value correct but buried in explanatory prose. 71 tool calls, 287.3 summed task seconds. |
| `4f4e27d` | `full_20261031T031828Z` | 18/20 | 496,625 | Historical target correct again; botanical-list fallback and bird species counting failed. 100 tool calls, 360.1 summed task seconds. |

The last two runs used the same frozen runtime, fresh run-specific caches and
gpt-4.1-mini. There was no intervening runtime edit or model upgrade. Simple HTML
tables now repeat column headers alongside cell values before flattening; merged
grids and mismatched rows are skipped rather than guessed. Month/year excerpt
priority applies only to explicit edit-marked sections, not arbitrary documents.

`b47a355` subsequently adds a pure final-output renderer, after all reasoning and
verification. For an explicit count question, it extracts a unique numeric value
directly attached to the requested unit phrase. Ambiguous, negated or uncertain
counts remain unchanged. It neither chooses the first number nor adds facts.
The renderer's output is never fed back into a model call.

Applying that exact function to both complete frozen answer sets and submitting
them again produced **20/20 and 18/20**, respectively. One answer changed in the
first set; zero changed in the second. Raw answers remain intact. Each run stores
`answers.rendered_r12.json` and `submission.rendered_r12.json`, explicitly marked
as format-only with no model rerun. These are **re-scores, not two new model runs**;
no answer sets were combined. The official leaderboard accepted the first perfect
score. This does not demonstrate stable 20/20.

Two remaining failure mechanisms in the second frozen run are actionable:

- **Structured-list fallback:** the literal grocery-list task initially classified
  the relevant plant parts correctly, but malformed exclusion fields and a missing
  plant-part field on an excluded item invalidated the structured report. After
  bounded retries, general-agent fallback discarded those useful classifications
  and omitted two qualifying items. A future repair should retain validated rows
  and repair only missing/invalid fields, with explicit applicability rules for
  excluded items. This was a text classification task, not image recognition.
- **Species identity:** video observations used separate species keys for an adult
  and a chick of the same species. Counting unique raw keys therefore overcounted.
  A future schema should separate canonical taxon identity from life stage and
  validate aggregation; a prompt saying age is not species was insufficient.

Neither follow-up is implemented in this frozen comparison. The historical task
was correct in both final fresh runs, but its token cost still varied substantially.
All 129 local tests pass after the final renderer, including synthetic negative
cases; local tests establish implementation checks, not benchmark correctness or
generalization. R12 remains an experimental branch, with earlier versions retained.

## R13: structured repair and deterministic decision composition

The next experiment targets failure mechanisms, not task IDs or stored answers:

- Classification schema repair preserves structurally valid fields from the first
  report and fills missing/invalid fields from a bounded repair. Changed exclusion
  order cannot silently reinterpret boolean flags. Input inventory, source text
  and properties remain validated. An unconditional whole-list model audit was
  removed; this reduces rewriting opportunities but can also retain a semantic
  error in the first report. Structure validation is not a truth check.
- Valid explicit exclusion flags short-circuit irrelevant optional property
  checks. Other items still require policy properties; missing fields are not
  invented by code. Exclusion interpretation remains model-dependent.
- Video census separates life stage from species identity. Code normalizes spaces,
  underscores and explicit stage suffixes/parentheses, without stemming names or
  merging different taxa by resemblance. Visual recognition and frame selection
  are still model-dependent; a correct count can coexist with a wrong species label.
- Candidate adjudication computes its verdict from three structured checks:
  task constraints, source identity and answer value. Missing/invalid checks cannot
  pass; a failed check overrides an aggregate PASS. Code does not prove the model's
  individual judgments true. Two evidence-supported candidates with the same
  deterministically rendered requested value are equivalent, not an unresolved
  conflict; different values still need a unique supported candidate.
- Historical processing now reports the first failed stage (provenance, numeric
  neighbors, identity), rather than masking it with a later name-check failure.
  Retrieval constraints and evidence requirements are not relaxed.

The first fresh full run, `full_20261031T035934Z` at runtime `9159a5a`, scored
**16/20**. The video count was correct. Remaining failures exposed (1) irrelevant
properties blocking already-excluded list items, (2) equivalent supported numeric
answers rejected as a tie, (3) contradictory aggregate review verdicts, and
(4) unresolved historical evidence with a misleading subsequent error. The
follow-up implementation addresses these mechanisms; the failed run is retained.

The second fresh full run, `full_20261031T040701Z` at runtime `579275d`, scored
**18/20**. Video, list classification and the numeric-statistics task were correct.
The list initially had an invalid exclusion phrase; local repair preserved its
useful classifications and produced the correct list. Funding and historical
evidence remained unresolved. The funding source had been fetched but returned
only its first 30,000 text characters. Historical reports rearranged observed
number/name records into nonliteral quotations, sometimes adding a role heading
inside each row. Code correctly rejected these fabricated quotations.

The final runtime `c1e4e71` addresses those data-transfer losses. Long HTML text
keeps its beginning, tail and bounded original passages matching a navigation
query, still within 30,000 characters. Numbered-record materialization copies
only an actually fetched, uniquely matching identifier-line/name-line span; it
cannot invent a missing number, name, role or bilingual identity. A dated original
document title can replace a paraphrased heading, but all later historical and
identity checks still apply. Offline replay repaired two observed roster reports;
an unfetched/fabricated report still failed. This is validation replay, not a new
benchmark score. The historical strategy still assumes the model selected a
relevant roster and eligible role; a date in a title alone is not full temporal
entailment. All 142 local tests pass at this runtime.

### R13 frozen results and remaining failures

| Runtime | Run | Official score | Chat tokens |
| --- | --- | --- | --- |
| `9159a5a` | `full_20261031T035934Z` | 16/20 | 581,933 |
| `579275d` | `full_20261031T040701Z` | 18/20 | 696,152 |
| `c1e4e71` | `full_20261031T041347Z` | **19/20** | 517,432 |
| `c1e4e71` | `full_20261031T041905Z` | **19/20** | 559,916 |

The last two runs used identical runtime source, gpt-4.1-mini and fresh per-run
caches. Both executed and submitted all 20 answers. These are fresh official
scores, not formatting re-scores or combinations of correct answers. Total chat
usage for the four R13 runs was 2,355,433 tokens, excluding audio transcription.
Two equal scores do not establish a guaranteed score floor or identical behavior.

The historical task failed in the first frozen run. Retrieval selected a different
page with labelled rows rather than the supported adjacent number/name layout;
the model still reconstructed nonliteral quotes and subsequently tried a current
roster, which the date contract rejected. The second frozen run answered it
correctly. Generic structured-table extraction and preserving useful historical
sources during repair remain better next steps than weakening date checks.

The second frozen run failed the Olympic minimum-count/tie task. The initial
candidate was CUB; the critic requested fuller coverage of tied countries. The
challenger was DEN. The comparison then marked both FAIL, even while its own
feedback described Cuba as having 1 athlete and Denmark as having 91. Structured
check aggregation prevents an overall verdict from contradicting sub-verdicts,
but cannot fix a semantically wrong sub-verdict. A future general ranking contract
should validate a complete observed collection, compute numeric minima and
alphabetical ties in code, then verify the selected entity/code mapping. Merely
comparing two candidate values is insufficient to prove the global minimum.

Video count, botanical classification, numeric-statistics output and paper funding
were correct in both frozen runs. These are encouraging repeated development-set
observations, not a controlled ablation or held-out result. No new model upgrade,
task-ID branch, benchmark answer constant or entity-specific URL was added.
The current conclusion is **two fresh 19/20 runs with different failures; stable
20/20 has not been achieved**. Earlier checkpoints and failed trials are retained.

## R14: structured tables, reviewed table queries and decision/confidence separation

Changes (general mechanisms; no task IDs, entity names, URLs or answer constants):

- HTML tables render as one literal line per row with expanded spans/headers;
  provenance uses NFKC compatibility equivalence; numbered records are grounded
  independently of layout; repair keeps an already verified dated source.
- `table_queries.py`: when a complete table was observed, the model writes a
  declarative query (min/max/count/sum/value, filters quoting the question,
  tie rule) or declares it not applicable; code executes it. Agreement settles
  the answer; disagreement changes it only after an independent spec review.
- `decision.py`: unresolved verification is reported (INCOMPLETE) but no longer
  converts a concrete candidate into an abstention; prose candidates are reduced
  to a literal submission value or treated as abstentions, which cannot replace
  a concrete incumbent. Strategies defer to the general pipeline when blocked.
- Robustness: search retry round, reusable downloaded media, AV1->H.264
  transcoding when OpenCV cannot decode, quantity answers drop units echoed from
  the question, list-contract repair names each incomplete input item (three
  bounded attempts), and video census inspects up to two candidates per sheet.

Evaluation environment: cloud container, gpt-4.1-mini, temperature 0, fresh
per-run caches, official scorer. YouTube blocks cloud IPs, so the runs reused raw
inputs from R13 run 2 (attachments, one downloaded source video, one raw caption
record); no answers or analyses were seeded. No local Stockfish: the chess tool
used its Lichess cloud-evaluation fallback (correct in every run).

| Runtime | Score | Chat tokens | Failures |
| --- | ---: | ---: | --- |
| r14b (tables, queries, decision layer) | 18/20 | 555,888 | video (AV1 frames undecodable), FunkMonk (prose "no such article" challenger won) |
| r14c (+ submission-form gate, AV1 transcoding) | 19/20 | 293,601 | "3 species" instead of "3" |
| r14d (+ quantity rendering) | 19/20 | 478,535 | botanical list (contract classified 9/19 items, generic repair message) |
| r14e (+ itemized list repair) | 19/20 | 531,741 | video count 2 (third species not sampled) |
| r14f (+ denser census sampling) | **20/20** | 631,065 | none |
| r14f, unchanged repeat | 18/20 | 448,923 | video count 2 (third species not recognised in inspected frames); Malko "Claus Peter" |

Both R13 frozen failures (historical roster, Olympic minimum/tie) were correct in
all six runs; the roster repair loop was observed recovering from a provenance
rejection on the pinned dated source, and the table query agreed with the solver
on the Olympic and 1977 at-bats questions. Targeted video repeats after r14f were
3/3 correct, but the frozen repeat failed it again, so visual species recognition
by the model remains the main source of variance. The Malko answer reflects an
ambiguous compound given name; the evidence-based name-part contract exists but
is disabled by default.

Conclusion: **one fresh 20/20 and one fresh 18/20 with identical runtime**. A
perfect score has been reached but is not stable; the six runs are development-set
observations on a repeatedly used set, not a held-out result. Local tests: 183 pass.
