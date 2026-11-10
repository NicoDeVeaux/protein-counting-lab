import Std

namespace PartitionCertificate

structure Interval where
  lo : Nat
  hi : Nat
  deriving Repr, DecidableEq

def Encloses (i : Interval) (x : Nat) : Prop := i.lo ≤ x ∧ x ≤ i.hi

inductive Factor where
  | constant : Nat → Factor
  | branch : Nat → Factor → Factor → Factor
  deriving Repr

abbrev Environment := Nat → Bool

def eval : Factor → Environment → Nat
  | .constant w, _ => w
  | .branch v left right, env => if env v then eval right env else eval left env

def factorBounds : Factor → Nat → Environment → Interval
  | .constant w, _, _ => ⟨w, w⟩
  | .branch v left right, depth, env =>
    if v < depth then
      if env v then factorBounds right depth env else factorBounds left depth env
    else
      let a := factorBounds left depth env
      let b := factorBounds right depth env
      ⟨min a.lo b.lo, max a.hi b.hi⟩

def Compatible (depth : Nat) (known assignment : Environment) : Prop :=
  ∀ v, v < depth → assignment v = known v

theorem factor_bounds_sound (factor : Factor) (depth : Nat)
    (known assignment : Environment) (h : Compatible depth known assignment) :
    Encloses (factorBounds factor depth known) (eval factor assignment) := by
  induction factor with
  | constant w => exact ⟨Nat.le_refl w, Nat.le_refl w⟩
  | branch v left right ihl ihr =>
    by_cases hv : v < depth
    · have heq := h v hv
      cases hb : known v
      · simpa [factorBounds, hv, eval, heq, hb] using ihl
      · simpa [factorBounds, hv, eval, heq, hb] using ihr
    · simp only [Encloses, factorBounds, ite_eq_right hv]
      cases hb : assignment v
      · simpa [eval, hb] using And.intro
          (Nat.le_trans (Nat.min_le_left (factorBounds left depth known).lo
              (factorBounds right depth known).lo) ihl.1)
          (Nat.le_trans ihl.2 (Nat.le_max_left (factorBounds left depth known).hi
              (factorBounds right depth known).hi))
      · simpa [eval, hb] using And.intro
          (Nat.le_trans (Nat.min_le_right (factorBounds left depth known).lo
              (factorBounds right depth known).lo) ihr.1)
          (Nat.le_trans ihr.2 (Nat.le_max_right (factorBounds left depth known).hi
              (factorBounds right depth known).hi))

def modelEval : List Factor → Environment → Nat
  | [], _ => 1
  | factor :: rest, env => eval factor env * modelEval rest env

def modelBounds : List Factor → Nat → Environment → Interval
  | [], _, _ => ⟨1, 1⟩
  | factor :: rest, depth, env =>
    let a := factorBounds factor depth env
    let b := modelBounds rest depth env
    ⟨a.lo * b.lo, a.hi * b.hi⟩

theorem model_bounds_sound (factors : List Factor) (depth : Nat)
    (known assignment : Environment) (h : Compatible depth known assignment) :
    Encloses (modelBounds factors depth known) (modelEval factors assignment) := by
  induction factors with
  | nil => exact ⟨Nat.le_refl 1, Nat.le_refl 1⟩
  | cons factor rest ih =>
    have hf := factor_bounds_sound factor depth known assignment h
    exact ⟨Nat.mul_le_mul hf.1 ih.1, Nat.mul_le_mul hf.2 ih.2⟩

def assign (env : Environment) (varIndex : Nat) (value : Bool) : Environment :=
  fun v => if v = varIndex then value else env v

theorem compatible_parent {depth : Nat} {known assignment : Environment} {bit : Bool}
    (h : Compatible (depth + 1) (assign known depth bit) assignment) :
    Compatible depth known assignment := by
  intro v hv
  have hne : v ≠ depth := by omega
  simpa [assign, hne] using h v (by omega)

def mass (factors : List Factor) (depth : Nat) : Nat → Environment → Nat
  | 0, env => modelEval factors env
  | remaining + 1, env =>
    mass factors (depth + 1) remaining (assign env depth false) +
    mass factors (depth + 1) remaining (assign env depth true)

theorem uniform_mass_bounds (factors : List Factor) (remaining depth lo hi : Nat)
    (env : Environment)
    (h : ∀ assignment, Compatible depth env assignment →
         lo ≤ modelEval factors assignment ∧ modelEval factors assignment ≤ hi) :
    lo * 2 ^ remaining ≤ mass factors depth remaining env ∧
    mass factors depth remaining env ≤ hi * 2 ^ remaining := by
  induction remaining generalizing depth env with
  | zero => simpa [mass] using h env (by intro v hv; rfl)
  | succ remaining ih =>
    have ha := ih (depth + 1) (assign env depth false)
      (by intro assignment hcomp; exact h assignment (compatible_parent hcomp))
    have hb := ih (depth + 1) (assign env depth true)
      (by intro assignment hcomp; exact h assignment (compatible_parent hcomp))
    have hs := And.intro (Nat.add_le_add ha.1 hb.1) (Nat.add_le_add ha.2 hb.2)
    simpa [mass, Nat.pow_succ, Nat.mul_add, Nat.mul_assoc, Nat.mul_two] using hs

def leafBounds (factors : List Factor) (depth remaining : Nat)
    (env : Environment) : Interval :=
  let bounds := modelBounds factors depth env
  ⟨bounds.lo * 2 ^ remaining, bounds.hi * 2 ^ remaining⟩

theorem leaf_bounds_sound (factors : List Factor) (depth remaining : Nat)
    (env : Environment) :
    Encloses (leafBounds factors depth remaining env) (mass factors depth remaining env) :=
  uniform_mass_bounds factors remaining depth _ _ env
    (fun assignment h => model_bounds_sound factors depth env assignment h)

inductive Cut where
  | leaf : Cut
  | split : Cut → Cut → Cut
  deriving Repr

def cutBounds (factors : List Factor) (depth remaining : Nat)
    (env : Environment) : Cut → Option Interval
  | .leaf => some (leafBounds factors depth remaining env)
  | .split left right => match remaining with
    | 0 => none
    | remaining + 1 => do
      let a ← cutBounds factors (depth + 1) remaining (assign env depth false) left
      let b ← cutBounds factors (depth + 1) remaining (assign env depth true) right
      pure ⟨a.lo + b.lo, a.hi + b.hi⟩

theorem cut_bounds_sound (factors : List Factor) (cut : Cut) (depth remaining : Nat)
    (env : Environment) (bounds : Interval)
    (h : cutBounds factors depth remaining env cut = some bounds) :
    Encloses bounds (mass factors depth remaining env) := by
  induction cut generalizing depth remaining env bounds with
  | leaf =>
    have heq : leafBounds factors depth remaining env = bounds := by simpa [cutBounds] using h
    rw [← heq]
    exact leaf_bounds_sound factors depth remaining env
  | split left right ihl ihr =>
    cases remaining with
    | zero => simp [cutBounds] at h
    | succ remaining =>
      cases ha : cutBounds factors (depth + 1) remaining (assign env depth false) left with
      | none => simp [cutBounds, ha] at h
      | some a =>
        cases hb : cutBounds factors (depth + 1) remaining (assign env depth true) right with
        | none => simp [cutBounds, ha, hb] at h
        | some b =>
          have heq : (⟨a.lo + b.lo, a.hi + b.hi⟩ : Interval) = bounds := by
            simpa [cutBounds, ha, hb] using h
          have hleft := ihl (depth + 1) remaining (assign env depth false) a ha
          have hright := ihr (depth + 1) remaining (assign env depth true) b hb
          rw [← heq]
          exact ⟨Nat.add_le_add hleft.1 hright.1, Nat.add_le_add hleft.2 hright.2⟩

def validFactor (n : Nat) : Factor → Bool
  | .constant _ => true
  | .branch varIndex left right =>
    varIndex < n && validFactor n left && validFactor n right

def validModel (n : Nat) (factors : List Factor) : Bool := factors.all (validFactor n)

theorem valid_factor_eval_congr (factor : Factor) (n : Nat)
    (a b : Environment) (hv : validFactor n factor = true)
    (hc : Compatible n a b) : eval factor a = eval factor b := by
  induction factor with
  | constant w => rfl
  | branch v left right ihl ihr =>
    have hp : (v < n ∧ validFactor n left = true) ∧ validFactor n right = true := by
      simpa [validFactor] using hv
    have heq := hc v hp.1.1
    simp [eval, heq, ihl hp.1.2, ihr hp.2]

theorem valid_model_eval_congr (factors : List Factor) (n : Nat)
    (a b : Environment) (hv : validModel n factors = true)
    (hc : Compatible n a b) : modelEval factors a = modelEval factors b := by
  induction factors with
  | nil => rfl
  | cons factor rest ih =>
    have hp : validFactor n factor = true ∧ validModel n rest = true := by
      simpa [validModel] using hv
    simp [modelEval, valid_factor_eval_congr factor n a b hp.1 hc, ih hp.2]

def check (n : Nat) (factors : List Factor) (cut : Cut) (claimed : Interval) : Bool :=
  validModel n factors && match cutBounds factors 0 n (fun _ => false) cut with
    | none => false
    | some actual => actual.lo == claimed.lo && actual.hi == claimed.hi

theorem check_model_valid (n : Nat) (factors : List Factor) (cut : Cut)
    (claimed : Interval) (h : check n factors cut claimed = true) :
    validModel n factors = true :=
  (Bool.and_eq_true_iff.mp h).1

theorem check_sound (n : Nat) (factors : List Factor) (cut : Cut) (claimed : Interval)
    (h : check n factors cut claimed = true) :
    Encloses claimed (mass factors 0 n (fun _ => false)) := by
  cases hb : cutBounds factors 0 n (fun _ => false) cut with
  | none => simp [check, hb] at h
  | some bounds =>
    have hp : validModel n factors = true ∧ bounds.lo = claimed.lo ∧ bounds.hi = claimed.hi := by
      simpa [check, hb] using h
    have heq := hp.2
    have hc := cut_bounds_sound factors cut 0 n (fun _ => false) bounds hb
    simpa [Encloses, ← heq.1, ← heq.2] using hc

structure State where
  n : Nat
  factors : List Factor
  cut : Cut
  claimed : Interval

def stateValue (state : State) : Nat := mass state.factors 0 state.n (fun _ => false)
def stateAccepted (state : State) : Prop := check state.n state.factors state.cut state.claimed = true

def RankAccepted (ac ap al bc bp bl : State) : Prop :=
  stateAccepted ac ∧ stateAccepted ap ∧ stateAccepted al ∧
  stateAccepted bc ∧ stateAccepted bp ∧ stateAccepted bl ∧
  0 < ap.claimed.lo * al.claimed.lo ∧ 0 < bp.claimed.lo * bl.claimed.lo ∧
  bc.claimed.hi * (ap.claimed.hi * al.claimed.hi) <
    ac.claimed.lo * (bp.claimed.lo * bl.claimed.lo)

instance (ac ap al bc bp bl : State) : Decidable (RankAccepted ac ap al bc bp bl) := by
  unfold RankAccepted stateAccepted
  infer_instance

def checkedGreater (ac ap al bc bp bl : State) : Bool :=
  decide (RankAccepted ac ap al bc bp bl)

theorem checked_greater_sound (ac ap al bc bp bl : State)
    (h : checkedGreater ac ap al bc bp bl = true) :
    0 < stateValue ap * stateValue al ∧ 0 < stateValue bp * stateValue bl ∧
    stateValue bc * (stateValue ap * stateValue al) <
      stateValue ac * (stateValue bp * stateValue bl) := by
  have accepted : RankAccepted ac ap al bc bp bl := of_decide_eq_true h
  rcases accepted with ⟨hac, hap, hal, hbc, hbp, hbl, hposA, hposB, hcross⟩
  have acb := check_sound ac.n ac.factors ac.cut ac.claimed hac
  have apb := check_sound ap.n ap.factors ap.cut ap.claimed hap
  have alb := check_sound al.n al.factors al.cut al.claimed hal
  have bcb := check_sound bc.n bc.factors bc.cut bc.claimed hbc
  have bpb := check_sound bp.n bp.factors bp.cut bp.claimed hbp
  have blb := check_sound bl.n bl.factors bl.cut bl.claimed hbl
  have lowA := Nat.mul_le_mul apb.1 alb.1
  have lowB := Nat.mul_le_mul bpb.1 blb.1
  have upper := Nat.mul_le_mul bcb.2 (Nat.mul_le_mul apb.2 alb.2)
  have lower := Nat.mul_le_mul acb.1 lowB
  exact ⟨Nat.lt_of_lt_of_le hposA lowA, Nat.lt_of_lt_of_le hposB lowB,
    Nat.lt_of_le_of_lt upper (Nat.lt_of_lt_of_le hcross lower)⟩

end PartitionCertificate

#print axioms PartitionCertificate.factor_bounds_sound
#print axioms PartitionCertificate.model_bounds_sound
#print axioms PartitionCertificate.compatible_parent
#print axioms PartitionCertificate.uniform_mass_bounds
#print axioms PartitionCertificate.leaf_bounds_sound
#print axioms PartitionCertificate.cut_bounds_sound
#print axioms PartitionCertificate.valid_factor_eval_congr
#print axioms PartitionCertificate.valid_model_eval_congr
#print axioms PartitionCertificate.check_model_valid
#print axioms PartitionCertificate.check_sound
#print axioms PartitionCertificate.checked_greater_sound
