import Lean
import PartitionCertificate

open Lean PartitionCertificate

partial def parseFactor (json : Json) : Except String Factor := do
  let fields ← json.getArr?
  match fields.toList with
  | [tag, weight] =>
    if (← tag.getStr?) != "c" then throw "factor tag"
    return .constant (← weight.getNat?)
  | [tag, varIndex, left, right] =>
    if (← tag.getStr?) != "b" then throw "factor tag"
    return .branch (← varIndex.getNat?) (← parseFactor left) (← parseFactor right)
  | _ => throw "factor shape"

partial def parseCut (json : Json) : Except String Cut := do
  match json with
  | .num _ =>
    if (← json.getNat?) != 0 then throw "leaf marker"
    return .leaf
  | .arr fields =>
    match fields.toList with
    | [left, right] => return .split (← parseCut left) (← parseCut right)
    | _ => throw "split shape"
  | _ => throw "cut shape"

def parseCertificate (line : String) : Except String (Nat × List Factor × Cut × Interval) := do
  let json ← Json.parse line
  let .obj fields := json | throw "object expected"
  let keys := fields.foldl (init := ([] : List String)) (fun xs key _ => key :: xs)
  if keys.length != 5 || !(keys.all fun k => ["n", "factors", "cut", "lower", "upper"].contains k)
    then throw "certificate fields"
  let n ← (← json.getObjVal? "n").getNat?
  let factorFields ← (← json.getObjVal? "factors").getArr?
  let factors ← factorFields.toList.mapM parseFactor
  let cut ← parseCut (← json.getObjVal? "cut")
  let lower ← (← json.getObjVal? "lower").getNat?
  let upper ← (← json.getObjVal? "upper").getNat?
  return (n, factors, cut, ⟨lower, upper⟩)

def answerLine (line : String) : String :=
  match parseCertificate line with
  | .error _ => "invalid"
  | .ok (n, factors, cut, claimed) =>
    if check n factors cut claimed then s!"accepted {claimed.lo} {claimed.hi}"
    else "rejected"

partial def checkLines (input output : IO.FS.Stream) : IO Unit := do
  let line ← input.getLine
  if line.isEmpty then return
  output.putStrLn (answerLine line)
  checkLines input output

def main : IO Unit := do
  checkLines (← IO.getStdin) (← IO.getStdout)
