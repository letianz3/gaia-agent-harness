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
