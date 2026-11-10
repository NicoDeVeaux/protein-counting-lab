# Prefreeze correction recheck

The previously reported large-offset multiplicity bug is resolved. `relative_scores` now separately sums all six signed GMEC terms and all six signed log-effective-conformation terms, then combines those relative quantities. It no longer derives the small ensemble correction by subtracting rounded absolute partition logs.

The reviewer reran the original synthetic counterexample: a common complex constant of `1e16`, one WT versus two mutant zero-energy conformers, and singleton zero-energy free states. The corrected ensemble change and explicit correction both equal `ln(2)` within `1e-14`; the GMEC change is zero. The added regression exercises that same behavior. No protein calculation was performed.

No blocking implementation issue remains from this review. The timer/RSS scopes, floating-point error and source-derived conformer-label qualifications recorded in the first review still apply. Independent source/reference checks remain required before scientific claims.
