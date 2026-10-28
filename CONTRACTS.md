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
