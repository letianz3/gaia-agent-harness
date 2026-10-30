# R7: code-owned task contracts

The model proposes semantic interpretations; Python owns validation, data flow,
arithmetic and output projection. These routes apply to task categories, never
task IDs, benchmark answers or a particular workbook's headers.

| Category | Model responsibility | Code responsibility |
|---|---|---|
| Simple wide-table sum | Identify explicit selection rules and classify each numeric column | Read original cells, require complete column/predicate coverage, apply inclusion/exclusion rules, sum with Decimal and format |
| First-name entity lookup | Propose concrete typed lookup steps, research each entity and identify name components | Validate predecessor joins and types; stop unresolved dependencies; return the final entity's first-name field |
| Source evidence | Select relevant retrieved evidence IDs | Preserve original excerpts and headings, hydrate IDs, check source provenance and entity mentions |

Unsupported table layouts defer to the existing general agent. Supported but
unresolved contracts terminate as INCOMPLETE rather than silently guessing.
Entity workers receive only their current step and verified predecessor evidence.
The normal tool loop remains available, with an explicit JSON terminal contract
when the tool budget expires. Each entity step has bounded initial and repair
budgets; the workflow cannot retry indefinitely.

## What this does not prove

The wide-table route is enabled by default. Strict entity chains are experimental
and require `AGENT_TYPED_ENTITIES_ENABLED=true`; they reduced coverage in R7's
first full run. Turning them off preserves the existing general lookup workflow.

- A real quotation mentioning two entities does not prove the claimed relation.
- Category membership, plan completeness and name segmentation still depend on
  the model. A fabricated but syntactically valid interpretation can pass.
- Strict evidence checks can reduce answer coverage when web retrieval fails.
- These are deliberately narrow routes: arbitrary spreadsheets, all naming
  conventions and arbitrary multi-hop questions are not solved deterministically.

## Validation

Synthetic tests cover missing columns, reversed exclusions, uncertain predicates,
formula cells, missing spreadsheet dimensions, type mismatches, dependent-step
blocking, cross-step evidence reuse, fabricated quotations, compound names and
structured output at budget exhaustion. They test execution invariants, not GAIA
factual accuracy. See EVALUATION.md for measured benchmark results.

During development, targeted runs exposed real implementation faults: absent
spreadsheet dimensions, placeholder plans, failure to reuse predecessor evidence,
and a generic terminal prompt overriding structured output. Each was repaired and
regression-tested. Subsequent actor failures also showed the cost of stricter
evidence requirements; rejected claims are preserved in local traces.

## R8: evidence resolution before synthesis

- **Visual census:** download up to 720p within the existing byte cap, inspect
  each contact sheet separately, select one candidate per segment, and reread
  individual frames. The model records visible identities, distinguishing traits
  and positions. Code deduplicates species keys within each frame and computes
  the maximum; it never unions species across different timestamps. Missing or
  uncertain frame records fail validation. Sampling and identity recognition can
  still miss species; this is an observed maximum, not exhaustive video analysis.
- **Classification:** supply item-specific source passages instead of only a
  global excerpt. Require literal question phrases for exclusions, then audit the
  proposal. For strict botanical vegetable requests, classify the consumed plant
  part and apply an explicit edible-root/stem/leaf/flower rule in code. This is a
  documented domain policy, not a universal definition of vegetable. There is no
  mapping from food names to answers; anatomical facts remain model-dependent.
- **Historical numeric neighbors:** prioritize dated search results, preserve
  navigation to archives, reject explicit conflicting update years at fetch time,
  and require quoted rows from a single dated source. Python selects target-1
  and target+1. Navigation labels cannot serve as factual evidence. A matching
  year alone does not prove month-specific validity, target identity or role;
  those semantic judgments still need source interpretation. This route supports
  exact adjacent numbers, not arbitrary nearest occupied positions.

All three are bounded routes layered around the ordinary tool loop. They add
evidence structure rather than additional free-form critics to every request.
