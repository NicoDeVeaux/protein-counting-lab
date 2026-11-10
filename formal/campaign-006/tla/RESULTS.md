# TLC cache checks

All 16 guard combinations, 5 properties and 2 worker counts.

| Workers | Identity | Generation | Revision | Nested | Property | Expected | Observed | States | Trace actions |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0 | 0 | 0 | 0 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 0 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 0 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 0 | CurrentRevision | violates | violates | 6011 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 0 | NoWidening | violates | violates | 6018 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 1 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 1 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 1 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 1 | CurrentRevision | violates | violates | 6011 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 0 | 1 | NoWidening | holds | holds | 21762 |  |
| 2 | 0 | 0 | 1 | 0 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 0 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 0 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 0 | CurrentRevision | holds | holds | 21222 |  |
| 2 | 0 | 0 | 1 | 0 | NoWidening | holds | holds | 21222 |  |
| 2 | 0 | 0 | 1 | 1 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 1 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 1 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 0 | 1 | 1 | CurrentRevision | holds | holds | 21222 |  |
| 2 | 0 | 0 | 1 | 1 | NoWidening | holds | holds | 21222 |  |
| 2 | 0 | 1 | 0 | 0 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 0 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 0 | Fresh | holds | holds | 17550 |  |
| 2 | 0 | 1 | 0 | 0 | CurrentRevision | violates | violates | 5843 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 0 | NoWidening | violates | violates | 5848 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 1 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 1 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 1 | Fresh | holds | holds | 17302 |  |
| 2 | 0 | 1 | 0 | 1 | CurrentRevision | violates | violates | 5843 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 0 | 1 | NoWidening | holds | holds | 17302 |  |
| 2 | 0 | 1 | 1 | 0 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 1 | 0 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 1 | 0 | Fresh | holds | holds | 17110 |  |
| 2 | 0 | 1 | 1 | 0 | CurrentRevision | holds | holds | 17110 |  |
| 2 | 0 | 1 | 1 | 0 | NoWidening | holds | holds | 17110 |  |
| 2 | 0 | 1 | 1 | 1 | Encloses | violates | violates | 129 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 1 | 1 | MatchingIdentity | violates | violates | 123 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 0 | 1 | 1 | 1 | Fresh | holds | holds | 17110 |  |
| 2 | 0 | 1 | 1 | 1 | CurrentRevision | holds | holds | 17110 |  |
| 2 | 0 | 1 | 1 | 1 | NoWidening | holds | holds | 17110 |  |
| 2 | 1 | 0 | 0 | 0 | Encloses | holds | holds | 16930 |  |
| 2 | 1 | 0 | 0 | 0 | MatchingIdentity | holds | holds | 16930 |  |
| 2 | 1 | 0 | 0 | 0 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 0 | 0 | CurrentRevision | violates | violates | 5663 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 0 | 0 | NoWidening | violates | violates | 5670 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 0 | 1 | Encloses | holds | holds | 16786 |  |
| 2 | 1 | 0 | 0 | 1 | MatchingIdentity | holds | holds | 16786 |  |
| 2 | 1 | 0 | 0 | 1 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 0 | 1 | CurrentRevision | violates | violates | 5663 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 0 | 1 | NoWidening | holds | holds | 16786 |  |
| 2 | 1 | 0 | 1 | 0 | Encloses | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 0 | MatchingIdentity | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 0 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 1 | 0 | CurrentRevision | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 0 | NoWidening | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 1 | Encloses | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 1 | MatchingIdentity | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 1 | Fresh | violates | violates | 711 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 0 | 1 | 1 | CurrentRevision | holds | holds | 16558 |  |
| 2 | 1 | 0 | 1 | 1 | NoWidening | holds | holds | 16558 |  |
| 2 | 1 | 1 | 0 | 0 | Encloses | holds | holds | 13906 |  |
| 2 | 1 | 1 | 0 | 0 | MatchingIdentity | holds | holds | 13906 |  |
| 2 | 1 | 1 | 0 | 0 | Fresh | holds | holds | 13906 |  |
| 2 | 1 | 1 | 0 | 0 | CurrentRevision | violates | violates | 5519 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 1 | 0 | 0 | NoWidening | violates | violates | 5524 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 1 | 0 | 1 | Encloses | holds | holds | 13846 |  |
| 2 | 1 | 1 | 0 | 1 | MatchingIdentity | holds | holds | 13846 |  |
| 2 | 1 | 1 | 0 | 1 | Fresh | holds | holds | 13846 |  |
| 2 | 1 | 1 | 0 | 1 | CurrentRevision | violates | violates | 5519 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 2 | 1 | 1 | 0 | 1 | NoWidening | holds | holds | 13846 |  |
| 2 | 1 | 1 | 1 | 0 | Encloses | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 0 | MatchingIdentity | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 0 | Fresh | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 0 | CurrentRevision | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 0 | NoWidening | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 1 | Encloses | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 1 | MatchingIdentity | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 1 | Fresh | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 1 | CurrentRevision | holds | holds | 13786 |  |
| 2 | 1 | 1 | 1 | 1 | NoWidening | holds | holds | 13786 |  |
| 1 | 0 | 0 | 0 | 0 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 0 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 0 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 0 | CurrentRevision | holds | holds | 176 |  |
| 1 | 0 | 0 | 0 | 0 | NoWidening | holds | holds | 176 |  |
| 1 | 0 | 0 | 0 | 1 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 1 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 1 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 0 | 1 | CurrentRevision | holds | holds | 176 |  |
| 1 | 0 | 0 | 0 | 1 | NoWidening | holds | holds | 176 |  |
| 1 | 0 | 0 | 1 | 0 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 0 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 0 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 0 | CurrentRevision | holds | holds | 176 |  |
| 1 | 0 | 0 | 1 | 0 | NoWidening | holds | holds | 176 |  |
| 1 | 0 | 0 | 1 | 1 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 1 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 1 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 0 | 1 | 1 | CurrentRevision | holds | holds | 176 |  |
| 1 | 0 | 0 | 1 | 1 | NoWidening | holds | holds | 176 |  |
| 1 | 0 | 1 | 0 | 0 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 0 | 0 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 0 | 0 | Fresh | holds | holds | 164 |  |
| 1 | 0 | 1 | 0 | 0 | CurrentRevision | holds | holds | 164 |  |
| 1 | 0 | 1 | 0 | 0 | NoWidening | holds | holds | 164 |  |
| 1 | 0 | 1 | 0 | 1 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 0 | 1 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 0 | 1 | Fresh | holds | holds | 164 |  |
| 1 | 0 | 1 | 0 | 1 | CurrentRevision | holds | holds | 164 |  |
| 1 | 0 | 1 | 0 | 1 | NoWidening | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 0 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 1 | 0 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 1 | 0 | Fresh | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 0 | CurrentRevision | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 0 | NoWidening | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 1 | Encloses | violates | violates | 45 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 1 | 1 | MatchingIdentity | violates | violates | 39 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 0 | 1 | 1 | 1 | Fresh | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 1 | CurrentRevision | holds | holds | 164 |  |
| 1 | 0 | 1 | 1 | 1 | NoWidening | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 0 | Encloses | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 0 | MatchingIdentity | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 0 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 1 | 0 | 0 | 0 | CurrentRevision | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 0 | NoWidening | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 1 | Encloses | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 1 | MatchingIdentity | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 1 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 1 | 0 | 0 | 1 | CurrentRevision | holds | holds | 164 |  |
| 1 | 1 | 0 | 0 | 1 | NoWidening | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 0 | Encloses | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 0 | MatchingIdentity | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 0 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 1 | 0 | 1 | 0 | CurrentRevision | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 0 | NoWidening | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 1 | Encloses | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 1 | MatchingIdentity | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 1 | Fresh | violates | violates | 106 | Initial predicate; Begin line 21, col 16 to line 27, col 72 of module BoundCache; Compute line 33, col 5 to line 39, col 96 of module BoundCache; Restart line 69, col 12 to line 74, col 73 of module BoundCache; Commit line 44, col 5 to line 65, col 27 of module BoundCache |
| 1 | 1 | 0 | 1 | 1 | CurrentRevision | holds | holds | 164 |  |
| 1 | 1 | 0 | 1 | 1 | NoWidening | holds | holds | 164 |  |
| 1 | 1 | 1 | 0 | 0 | Encloses | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 0 | MatchingIdentity | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 0 | Fresh | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 0 | CurrentRevision | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 0 | NoWidening | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 1 | Encloses | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 1 | MatchingIdentity | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 1 | Fresh | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 1 | CurrentRevision | holds | holds | 152 |  |
| 1 | 1 | 1 | 0 | 1 | NoWidening | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 0 | Encloses | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 0 | MatchingIdentity | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 0 | Fresh | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 0 | CurrentRevision | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 0 | NoWidening | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 1 | Encloses | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 1 | MatchingIdentity | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 1 | Fresh | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 1 | CurrentRevision | holds | holds | 152 |  |
| 1 | 1 | 1 | 1 | 1 | NoWidening | holds | holds | 152 |  |

rows=160 mismatches=0
