import Certificate

open CertifiedRank

def parseBounds (line : String) : Option (RatioBounds × RatioBounds) := do
  let fields := (line.splitToList Char.isWhitespace).filter (fun s => !s.isEmpty)
  let values ← fields.mapM String.toNat?
  match values with
  | [anl, anu, adl, adu, bnl, bnu, bdl, bdu] =>
      some (⟨⟨anl, anu⟩, ⟨adl, adu⟩⟩, ⟨⟨bnl, bnu⟩, ⟨bdl, bdu⟩⟩)
  | _ => none

partial def checkLines (input output : IO.FS.Stream) : IO Unit := do
  let line ← input.getLine
  if line.isEmpty then return
  let answer := match parseBounds line with
    | none => "invalid"
    | some (a, b) => if check a b then "accepted" else "rejected"
  output.putStrLn answer
  checkLines input output

def main : IO Unit := do
  checkLines (← IO.getStdin) (← IO.getStdout)
