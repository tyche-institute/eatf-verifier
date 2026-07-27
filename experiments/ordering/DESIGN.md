# Legal-ordering study — design, fixed before any measurement

This file specifies the experiment that Section 2.4 of the SNCS manuscript
promises and does not yet deliver. It is written before the harness exists so
that the design, the predictions and the honest scoping cannot be adjusted to
whatever the numbers turn out to be.

## What Section 2.4 currently promises

The manuscript quotes ETSI EN 319 102-1, whose processing clause permits "any
ordering that produces the same results", observes that the standard therefore
presumes result-invariance under reordering and supplies no discipline for
confirming it, and says "That is the gap this article addresses." The article
as it stands measures agreement under **one** ordering. This experiment is what
would close that gap.

## The measurement

For each case in a corpus, determine its **fault set**: the set of guards in
the specified procedure that the case violates, independently of the order in
which guards run.

- A case with a fault set of size 1 is **order-invariant**: every legal
  ordering assigns it the same first-failure code, and that fact is analytic,
  not measured.
- A case with a fault set of size greater than 1 is **order-dependent**: which
  code it receives depends on which of its violated guards runs first, and the
  standard's permission to reorder therefore does not preserve the code.

The two numbers to report are: the fraction of legal orderings preserving the
**verdict** on every case, and the fraction preserving the complete
**first-failure code** assignment.

## Predictions, recorded now

1. **Verdict invariance will be 100%.** This is arithmetic and must be reported
   as analytic rather than measured: a package violating guard G violates it
   under every ordering, so the verdict cannot change. It is included only as
   the contrast that gives the code result meaning.
2. **Code invariance will be strictly below 100%**, because the two naive cases
   of `../path-shadowing` are already known to violate two guards each.
3. The order-dependent cases will be exactly those whose construction touches
   an entry that the signed receipt also names as a witness.

Prediction 3 is the falsifiable one. If order-dependence appears in a case with
no witness-reference involvement, the explanation above is wrong and must be
reported as wrong.

## Two candidate harnesses

**(a) Collect mode.** Add a non-short-circuiting mode behind a flag to both
verifiers: where the next guard's inputs remain well defined after a failure,
append the failure and continue instead of returning. The shipped default must
be untouched and every existing test must stay green — that is the acceptance
criterion, not an aspiration. Cost: the higher of the two, roughly 3–5 days
across two 450-line implementations, and it changes files that the article's
other results depend on.

**(b) Repair peeling.** Leave both verifiers untouched. For each case, run the
verifier, apply the minimal repair for whatever code it returned, and re-run,
until the package is accepted. The sequence of codes observed is the case's
fault set in pipeline order, and its length is the fault-set size. Cost: lower
and better isolated, but it requires writing one repair operator per rejection
code, and a repair that changes more than the single fault it targets would
silently corrupt the measurement.

**(b) is preferred** on risk grounds: it cannot regress shipped behaviour, and
its failure mode — an over-broad repair — is detectable by asserting that each
repair changes exactly the bytes it claims to change.

## Scoping that must appear in any write-up

- The enumerated ordering space comes from **our** dependency analysis of
  **our** procedure. It is not a property of EN 319 102-1. Every sentence must
  say "orderings legal for this procedure under the data dependencies reported
  in Table X".
- The reading of "results" in the ETSI clause is load-bearing and must be
  declared. If "results" includes the sub-indication, then the standard already
  forbids order-dependent codes and the finding becomes that reordering
  implementations would violate the clause. If it means the top-level status
  only, the finding is that the permission is sound for verdicts and silent
  about the sub-indications the same standard requires. State which reading is
  taken and why; do not let the sentence work under both.
- **States are not codes.** Table 2 of the manuscript lists 13 ordered states;
  the TypeScript implementation declares 27 failure codes; the 21-case corpus
  exercises 16 distinct rejection codes. Any sentence mixing the three counts
  is wrong.
- No shadowing **rate** may be derived from four cases, and none may be stated
  as a property of short-circuiting verifiers generally.

## Abort condition

If the harness is not producing consistent results in both languages by
8 August 2026, stop and submit without this section. A finished article left
unsubmitted is this lane's actual failure mode.
