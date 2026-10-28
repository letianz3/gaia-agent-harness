# Per-task failure ledger

This ledger distinguishes transport/format checks from factual correctness.
Known development questions informed diagnosis; no task IDs or answer keys were
added to runtime routing. These are engineering iterations, not held-out evidence.

## Reference: 14/20 run `full_20261028T004401Z`

| Task prefix | Observed failure | Failure stage | Next bounded experiment |
|---|---|---|---|
| a1e91b78 | Different species collapsed into one generic category; later detail sampling missed decisive frames | Visual observation and frame selection | Track distinct visual entities across whole-video coverage before selecting close-ups; do not use a few selected frames to claim global absence |
| cca530fc | Image transcribed into the wrong square coordinates/pieces; engine score then misinterpreted | Perception before computation | Validate a coordinate-labelled piece inventory before engine analysis; valid FEN alone is insufficient |
| 3cef3a44 | Not all original list items considered; later trials confused everyday and technical category definitions | Coverage and semantic classification | Account for all items, research ambiguous technical properties, evaluate explicit exclusions separately, render with code |
| 99c9cc74 | Correct source transcript was paraphrased during worker/synthesis stages | Source transformation | Select contiguous original phrases, validate source membership, sort/render without another prose rewrite |
| 305ac316 | Missing actor identity treated as completed work; later role lookup guessed | Prerequisite and source acquisition | Retrieve identity and role evidence as one linked evidence chain; NOT_FOUND must not become a factual premise |
| a0c07678 | Missing historical roster replaced by incomplete/current records and guessed adjacent numbers | Temporal source completeness | Require dated roster coverage before adjacency calculation; bounded source fallback cannot substitute for the missing roster |

## Regression controls from the previous experiments

| Task prefix | Regression | Guardrail for this iteration |
|---|---|---|
| 840bfca7 | Wrong award identifier or verbose output despite finding a related paper | Keep existing web/planning/synthesis path unchanged; new routing must not capture external-source questions |
| 7bd855d8 | Food/drink membership changed, changing the spreadsheet total | Keep file/Python path unchanged; input-block routing must not capture spreadsheets |
| 4fc2f1ae / cabe07ed | Overly broad unavailable policy discarded previously correct retrieval results | Do not reintroduce the previous global completion-contract prompt |

## Version preservation

- `main` initially retains the measured 14/20 runtime (`ea7a1dd`) plus its report
  (`e96ec6d`); tag `stable/gaia-14of20-ea7a1dd` preserves that starting point.
- `experiment/evidence-contract-v1`, commit `25ac623`: exact archived v1 runtime,
  measured 12/20. Source snapshot remains in its local run directory.
- `experiment/evidence-contract-v2`, commit `64f0b01`: corrected experiment and
  regression tests, measured 13/20. Original patch and edited files also remain.
- `experiment/source-grounding-v3`: isolated list workflow, starting from stable
  main rather than importing the unsuccessful global changes.

## Source-grounding iteration sequence

1. `03cea10`: exact source spans and complete item accounting. Targeted recipe
   output improved; classification recovered the omitted item but added excluded
   items. Coverage validation cannot establish correct category membership.
2. `32c3421`: separate target membership from explicit exclusion flags. The
   targeted classification still failed: the model set exclusion flags incorrectly.
3. `392ad9c`: bounded web research before technical classification (maximum three
   tool-loop turns). The targeted list now met the requested technical distinction.
   Recipe extraction needs no external lookup. Full-run validation follows.

Routing is deliberately narrow: alphabetized comma-separated answers with an
actual transcript or a standalone explicit input list. All other tasks keep the
reference execution path. A malformed list contract gets at most one repair;
failure or explicit deferral falls back to the ordinary agent.

Program checks validate exact source spans, all-item coverage, boolean decisions,
duplicate handling, exclusion application and sorting. They do **not** validate
whether a model-assigned semantic category is true, whether transcription is
perfect, or whether all relevant phrases were extracted. New unit tests use
synthetic examples rather than benchmark answers. Research observations can still
be incomplete, and model/website variability can change unaffected tasks.

Every full experiment now records its Git commit and tracked-change status in
`version.json`, in addition to the existing source snapshot and raw traces.
Runtime artifacts remain local under `.runs/`; source versions are Git branches.


## Full v3 result

`full_20261028T030837Z`, runtime commit `392ad9c`, official **15/20 (75%)**.
413,810 chat tokens (-4.1% vs 431,574); 285.560 summed agent seconds; 73 tool calls.
Both intentionally targeted questions improved. The unchanged actor path also
improved, while spreadsheet category selection and historical nationality
regressed. Net: three gains, two regressions. Those incidental changes cannot
be attributed to the new routing. Fifty local tests passed.

The five remaining misses, inspected individually:
- Video: generic penguin label still collapses distinct species; critic echoes
  the tool's conclusion rather than examining independent visual evidence.
- Chess: vision-to-FEN tool failed; a worker then produced a correct occupied-square
  inventory, but downstream reasoning guessed a move instead of using an engine.
- Historical roster: a current active roster was treated as the July 2023 roster;
  a lower number was chosen without complete dated adjacency evidence.
- Spreadsheet: one worker recognized dessert as not a drink, yet left it out of
  food totals; the critic later relabelled it as a drink. Arithmetic was correct
  for the wrong inclusion set.
- Historical nationality: current nationality labels hid the former country;
  recovery found a more plausible candidate but failed the requested first-name
  format and lacked direct historical nationality evidence.

Next bounded iteration: structured occupied-square transcription and deterministic
FEN construction, legal-position validation, then engine evaluation. Preserve the
15/20 version before changing this one capability. No board positions or moves
from the benchmark are embedded in the implementation.


## Structured-chess v4 result

First attempt (`bd38b74`): direct screen-grid JSON remained visually wrong;
legality validation accepted an incorrect position. Targeted result failed.
Second attempt (`042b2e3`): detect the regular two-color grid, crop/label all 64
cells, classify pieces in two 32-cell sheets, read axes separately, then construct
FEN in code and run the engine. This succeeded in both the targeted test and the
full run. Non-regular images fall back to bounded whole-image transcription.
Two-color segmentation is limited to regular digital boards, and legal inventory
does not prove correct recognition. Castling/en-passant history is not inferable
from a still image and is not assumed.

Full run `full_20261028T032004Z`, runtime commit `042b2e3`, official **16/20 (80%)**:
350,250 chat tokens, 255.186 summed agent seconds, 169 model calls, 64 tool calls.
Against the original 14/20 run: tokens -18.8%, summed agent latency -25.3%.
Against v3: one additional correct answer, but category classification regressed
while spreadsheet and historical nationality recovered. These cross-task changes
occurred without corresponding runtime changes and are not causal evidence for
the chess mechanism. V4 and v3 full runs together used 764,060 chat tokens, plus
separate targeted probes and uncounted audio transcription. No answer mixing.

56 local tests passed. Code hashes match the preserved full-run source snapshot.

### Remaining four failures after v4 (each trace inspected)

| Task | Evidence of failure | Proposed next test |
|---|---|---|
| Bird species | Tool summary groups different birds into a generic category; critic only repeats that summary | Whole-video entity inventory and species-discriminating close-ups; avoid treating sampled absence as proof |
| Botanical list | Research fetched generic definitions rather than verifying the ambiguous item's organ/type; coverage passed but the exclusion flag was wrong | Retrieve item-specific evidence for ambiguous membership; cite the factual property before applying exclusion rules |
| NASA funding | Correct article/paper identified, but funding paragraph was not retrieved; solver still supplied an unsupported identifier | Follow full-text/PDF routes and inspect acknowledgements; link the named author to the exact funding span, not a nearby grant |
| Historical roster | Current active roster was used for a July 2023 question | Acquire an explicitly dated complete roster, then compute numeric adjacency; no current-page substitution |

Stable v4 retains the source-list mechanism because recipe extraction reproduced
and the combined run improved. Botanical classification remains explicitly
unresolved despite one earlier correct full-run answer. It must not be presented
as a reliable fix. Other unchanged tasks can still regress on the next run.


## R6: bounded PDF access

Runtime commit `c5c7ebb`, run `full_20261028T034633Z`, official **15/20**,
348,129 chat tokens (R5: 350,250). 59 unit tests passed. Config and run trace
both request `gpt-4.1-mini`; audio uses `gpt-4o-mini-transcribe` by default.
No model switch was made.

The funding-task trace exposed a concrete capability failure: the paper PDF was
rejected by the shared 3 MB limit. A first 20 MB budget still failed; the public
response reported 33,306,077 bytes. The final implementation streams the body,
recognizes PDF by magic bytes, caps PDFs at 50 MB and other content at 3 MB,
closes responses on errors, and retains the beginning and end of long PDF text.
It has no task IDs, paper URLs or award numbers embedded in runtime code.
The paper became readable and the funding answer was correct in targeted and
full tests. The critic still lacked the precise funding passage because raw
observations are truncated before evidence-packet construction. This is a
separate context-delivery problem for a future bounded source-reread mechanism.

Per-task comparison with R5: funding and classification gained; actor, spreadsheet
and historical-first-name outputs regressed. Net minus one. The classification
path did not change; its gain is not evidence of a new semantic fix. The three
regressions cannot be causally attributed to the PDF fix from this comparison.

Remaining five misses inspected individually:
- Video: generic bird-group summaries still fail to distinguish simultaneous species.
- Historical roster: current roster still substituted for the requested historical date.
- Actor: identity found, downstream role search failed; synthesis returned the actor's
  first name instead of the character's first name.
- Spreadsheet: a dessert category again omitted despite only drinks being excluded.
- Historical first name: correct person approached, but response included an extra
  given-name component; historical-nationality evidence remained incomplete.

Decision: retain the complete R6 experiment on `experiment/bounded-pdf-r6`;
do not replace the evaluated R5 default on one lower-scoring run. Record the
confirmed PDF capability repair separately from end-to-end benchmark variance.
All source snapshots, targeted traces and submissions remain local. No scores
are assembled by mixing answer sets.
