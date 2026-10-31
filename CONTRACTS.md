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


## R9: separate mechanism, strategy and domain interpretation

`agent.py` calls `workflows.solve_specialized` before its general loop. The
strategy dispatcher records its selection or general fallback in the trace.
`AGENT_SPECIALIZED_WORKFLOWS_ENABLED=false` bypasses this dispatch and specialized
video census while keeping ordinary tools and the general agent available.

`policies.py` owns domain interpretation. Its PropertyPolicy declares a field,
vocabulary, aliases, accepted values and instructions. The list executor performs
coverage, provenance, exclusions and formatting without embedding accepted plant
parts. A synthetic material-conductivity policy exercises the same executor.
`AGENT_DOMAIN_POLICIES_ENABLED=false` disables automatic domain interpretation
while retaining source-list extraction and generic classification.

The botanical policy only activates for explicit exclusion of botanical fruits
from vegetables, and conservatively abstains on culinary/everyday requests. This
is a policy choice with limited scope, not a universal vegetable definition.
The temporal strategy requires surname output and exact adjacent numbers;
version ordering, alphabetical and nearest-occupied requests do not enter it.
A recently updated document is not rejected merely for its update year when it
contains an explicitly dated historical roster section. Month validity and row
scope still require evidence interpretation. Video census additionally requires
a maximum/count question; describing simultaneous interactions is insufficient.

Negative routing tests and the six non-GAIA model smoke cases provide evidence
against specific accidental interceptions. Wider unseen-task evaluations remain
necessary; retaining 18/20 on the development set does not establish that.

## Tables, record grounding and ranking (R14 candidate)

`web_tables.py` renders every HTML data table as one delimited line per row inside
`[TABLE n: R rows x C columns]` / `[END TABLE n]` markers. Colspan/rowspan and
multi-row headers (including `<td>`-styled headers) expand into named columns;
data colspans are shown once, rowspans repeat. The rendered text IS the
observation, so a copied row is a literal source span, and code parses the same
text back. Blocks interrupted by long-document truncation are marked incomplete.
This replaces per-cell `Header: value` labels, which produced multi-line records
that models re-joined into nonliteral quotations. Evidence windows inside a table
receive the table's literal header line as a separate span.

Provenance comparison uses NFKC compatibility equivalence (`contracts.canonical`):
full-width digits, letters and spaces match their ASCII forms. Reordering,
rewording or a different number still fails.

`literal_numbered_records` pairs an identifier with a name independently of
layout: table rows, alternating identifier/name lines (orientation read from the
end of the run), and labelled field blocks. The nearest identifier wins; a nearer
or equally near conflicting identifier means the claimed pair was not observed.

When a historical-roster report establishes a valid dated source but fails only
row provenance, repair keeps that source (`dated_source_valid`) and shows its
literal rows; the repair prompt no longer forbids citing already-fetched pages.

`table_queries.py` generalizes this to any answer computable from one complete observed
table: min/max (with an explicit tie rule), count, sum, or the value of the single
row matching filters. There is no question regex: the model either writes a query
spec (table, operation, column indices, filters that each quote the question
phrase they implement, tie rule) or declares it not applicable. Code validates
the spec, ignores blank/aggregate rows, refuses mostly non-numeric value columns
and unbroken ties, and executes it. Agreement with the solver settles the answer.
Disagreement changes the answer only after an independent review of the SPEC's
semantics (scope, column meaning, every bound) passes; code still does the
counting and ranking. A failed review leaves the ordinary critic path in charge.

## Verification and decision layers

`agent._recover_answer` runs fixed stages: explicit format repair, computable
answers (above), independent evidence critique, one targeted acquisition or an
evidence-backed correction, the computation stage again on enlarged evidence, then
candidate comparison. `decision.py` separates answer selection from confidence:
unresolved verification is recorded (`answer_verification_unresolved`, run status
INCOMPLETE) and the answer is the candidate favoured by the structured comparison
checks (PASS 1, UNCERTAIN 0, FAIL -2), incumbent on ties, abstention strings never
preferred. `AGENT_ABSTAIN_ON_UNVERIFIED=true` restores strict abstention.

Contract strategies no longer abstain when blocked. The table-sum and entity-chain
contracts defer to the general pipeline. The historical-roster contract returns its
least severe rejected candidate only when the dated source itself was verified and
only quotation/name-bridge provenance remained unresolved; role, neighbor and
period failures fall through to the general pipeline.

## Degradation and schema normalization (R15)

Contracts degrade at the smallest failing unit. Video census excludes only the
uncertain or under-described groups (and labels the count a lower bound) rather
than failing the whole observation. List classification accepts any unambiguous
flag representation and rejects only ambiguous ones, with an itemised repair
request. Output rendering reduces a "first name" request to one given name
(hyphenated compounds stay whole) alongside the existing quantity rendering.
