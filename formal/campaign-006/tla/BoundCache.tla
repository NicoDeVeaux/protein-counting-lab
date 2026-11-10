------------------------------ MODULE BoundCache ------------------------------
EXTENDS Naturals, TLC

CONSTANTS Workers, GuardIdentity, GuardGeneration, GuardRevision, GuardNested
VARIABLES generation, revision, lower, upper, jobs, identityOK, ageOK, revisionOK, nestedOK
vars == <<generation, revision, lower, upper, jobs, identityOK, ageOK, revisionOK, nestedOK>>
Keys == {"A", "B"}
Truth(k) == IF k = "A" THEN 1 ELSE 2
Idle == [phase |-> "idle", key |-> "A", resultKey |-> "A", gen |-> 0, rev |-> 0,
         lo |-> 0, hi |-> 3, resultLo |-> 0, resultHi |-> 3]

(* core.py: BoundCache.__init__ and register; two different complete model keys. *)
Init == /\ generation = 0
        /\ revision = [k \in Keys |-> 0]
        /\ lower = [k \in Keys |-> 0]
        /\ upper = [k \in Keys |-> 3]
        /\ jobs = [w \in Workers |-> Idle]
        /\ identityOK = TRUE /\ ageOK = TRUE /\ revisionOK = TRUE /\ nestedOK = TRUE

(* core.py: BoundCache.begin, atomic snapshot before trusted computation. *)
Begin(w, k) == /\ jobs[w].phase = "idle"
               /\ jobs' = [jobs EXCEPT ![w] =
                    [phase |-> "computing", key |-> k, resultKey |-> k, gen |-> generation,
                     rev |-> revision[k], lo |-> lower[k], hi |-> upper[k],
                     resultLo |-> 0, resultHi |-> 3]]
               /\ UNCHANGED <<generation, revision, lower, upper,
                               identityOK, ageOK, revisionOK, nestedOK>>

(* The producer is numerically trusted for its resultKey. Delivery may mix up two
   results, so commit must check that resultKey is the requested complete key.
   The bound also fits the ticket snapshot; otherwise nesting rejects it anyway. *)
Compute(w, resultKey, lo, hi) ==
    /\ jobs[w].phase = "computing"
    /\ jobs[w].lo <= lo /\ lo <= Truth(resultKey)
    /\ Truth(resultKey) <= hi /\ hi <= jobs[w].hi
    /\ jobs' = [jobs EXCEPT ![w].phase = "ready",
                            ![w].resultKey = resultKey,
                            ![w].resultLo = lo, ![w].resultHi = hi]
    /\ UNCHANGED <<generation, revision, lower, upper, identityOK, ageOK, revisionOK, nestedOK>>

(* core.py: BoundCache.commit. All validation and replacement occur without yield.
   Independent switches remove actual guards; they are deliberate mutants. *)
Commit(w) ==
    /\ jobs[w].phase = "ready"
    /\ LET j == jobs[w]
           k == j.key
           sameKey == j.resultKey = k
           fresh == j.gen = generation
           current == j.rev = revision[k]
           nested == lower[k] <= j.resultLo /\ j.resultHi <= upper[k]
           accept == (GuardIdentity => sameKey)
                  /\ (GuardGeneration => fresh)
                  /\ (GuardRevision => current)
                  /\ (GuardNested => nested)
       IN /\ jobs' = [jobs EXCEPT ![w].phase = "done"]
          /\ IF accept
             THEN /\ revision' = [revision EXCEPT ![k] = @ + 1]
                  /\ lower' = [lower EXCEPT ![k] = j.resultLo]
                  /\ upper' = [upper EXCEPT ![k] = j.resultHi]
                  /\ identityOK' = (identityOK /\ sameKey)
                  /\ ageOK' = (ageOK /\ fresh)
                  /\ revisionOK' = (revisionOK /\ current)
                  /\ nestedOK' = (nestedOK /\ nested)
             ELSE UNCHANGED <<revision, lower, upper, identityOK, ageOK, revisionOK, nestedOK>>
    /\ UNCHANGED generation

(* core.py: BoundCache.restart plus register before another callback is delivered.
   A single restart is enough to expose revision reuse with an old ticket. *)
Restart == /\ generation = 0
           /\ generation' = 1
           /\ revision' = [k \in Keys |-> 0]
           /\ lower' = [k \in Keys |-> 0]
           /\ upper' = [k \in Keys |-> 3]
           /\ UNCHANGED <<jobs, identityOK, ageOK, revisionOK, nestedOK>>

Next == (\E w \in Workers, k \in Keys : Begin(w, k))
     \/ (\E w \in Workers, k \in Keys, lo \in 0..3, hi \in 0..3 : Compute(w, k, lo, hi))
     \/ (\E w \in Workers : Commit(w)) \/ Restart
Spec == Init /\ [][Next]_vars
Encloses == \A k \in Keys : lower[k] <= Truth(k) /\ Truth(k) <= upper[k]
MatchingIdentity == identityOK
Fresh == ageOK
CurrentRevision == revisionOK
NoWidening == nestedOK
=============================================================================
