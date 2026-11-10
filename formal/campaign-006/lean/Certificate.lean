import Std

namespace CertifiedRank

structure Interval where
  lo : Nat
  hi : Nat
  deriving Repr

def Encloses (i : Interval) (x : Nat) : Prop := i.lo ≤ x ∧ x ≤ i.hi

def add (a b : Interval) : Interval := ⟨a.lo + b.lo, a.hi + b.hi⟩
def mul (a b : Interval) : Interval := ⟨a.lo * b.lo, a.hi * b.hi⟩

theorem add_sound {a b : Interval} {x y : Nat}
    (ha : Encloses a x) (hb : Encloses b y) : Encloses (add a b) (x + y) :=
  ⟨Nat.add_le_add ha.1 hb.1, Nat.add_le_add ha.2 hb.2⟩

theorem mul_sound {a b : Interval} {x y : Nat}
    (ha : Encloses a x) (hb : Encloses b y) : Encloses (mul a b) (x * y) :=
  ⟨Nat.mul_le_mul ha.1 hb.1, Nat.mul_le_mul ha.2 hb.2⟩

def sumIntervals : List Interval → Interval
  | [] => ⟨0, 0⟩
  | i :: rest => add i (sumIntervals rest)

def productIntervals : List Interval → Interval
  | [] => ⟨1, 1⟩
  | i :: rest => mul i (productIntervals rest)

def sumValues : List Nat → Nat
  | [] => 0
  | x :: rest => x + sumValues rest

def productValues : List Nat → Nat
  | [] => 1
  | x :: rest => x * productValues rest

inductive PointwiseEncloses : List Interval → List Nat → Prop where
  | nil : PointwiseEncloses [] []
  | cons {i : Interval} {x : Nat} {is : List Interval} {xs : List Nat} :
      Encloses i x → PointwiseEncloses is xs → PointwiseEncloses (i :: is) (x :: xs)

theorem sum_sound {is : List Interval} {xs : List Nat}
    (h : PointwiseEncloses is xs) : Encloses (sumIntervals is) (sumValues xs) := by
  induction h with
  | nil => exact ⟨Nat.le_refl 0, Nat.le_refl 0⟩
  | cons hi _ ih => exact add_sound hi ih

theorem product_sound {is : List Interval} {xs : List Nat}
    (h : PointwiseEncloses is xs) : Encloses (productIntervals is) (productValues xs) := by
  induction h with
  | nil => exact ⟨Nat.le_refl 1, Nat.le_refl 1⟩
  | cons hi _ ih => exact mul_sound hi ih

structure RatioBounds where
  numerator : Interval
  denominator : Interval
  deriving Repr

def WellFormed (a : RatioBounds) : Prop :=
  a.numerator.lo ≤ a.numerator.hi ∧
  a.denominator.lo ≤ a.denominator.hi ∧
  0 < a.denominator.lo

def Accepts (a b : RatioBounds) : Prop :=
  WellFormed a ∧ WellFormed b ∧
  b.numerator.hi * a.denominator.hi < a.numerator.lo * b.denominator.lo

instance (a b : RatioBounds) : Decidable (Accepts a b) := by
  unfold Accepts WellFormed
  infer_instance

def check (a b : RatioBounds) : Bool := decide (Accepts a b)

theorem check_sound {a b : RatioBounds} {an ad bn bd : Nat}
    (hcheck : check a b = true)
    (han : Encloses a.numerator an) (had : Encloses a.denominator ad)
    (hbn : Encloses b.numerator bn) (hbd : Encloses b.denominator bd) :
    0 < ad ∧ 0 < bd ∧ bn * ad < an * bd := by
  have h : Accepts a b := of_decide_eq_true hcheck
  have hlow : a.numerator.lo * b.denominator.lo ≤ an * bd :=
    Nat.mul_le_mul han.1 hbd.1
  have hupp : bn * ad ≤ b.numerator.hi * a.denominator.hi :=
    Nat.mul_le_mul hbn.2 had.2
  exact ⟨Nat.lt_of_lt_of_le h.1.2.2 had.1,
    Nat.lt_of_lt_of_le h.2.1.2.2 hbd.1,
    Nat.lt_of_le_of_lt hupp (Nat.lt_of_lt_of_le h.2.2 hlow)⟩

def threeState (c p l : Interval) : RatioBounds := ⟨c, mul p l⟩

theorem three_state_sound {c p l : Interval} {cv pv lv : Nat}
    (hc : Encloses c cv) (hp : Encloses p pv) (hl : Encloses l lv) :
    Encloses (threeState c p l).numerator cv ∧
    Encloses (threeState c p l).denominator (pv * lv) :=
  ⟨hc, mul_sound hp hl⟩

theorem three_state_rank_sound {ac ap al bc bp bl : Interval}
    {acv apv alv bcv bpv blv : Nat}
    (hcheck : check (threeState ac ap al) (threeState bc bp bl) = true)
    (hac : Encloses ac acv) (hap : Encloses ap apv) (hal : Encloses al alv)
    (hbc : Encloses bc bcv) (hbp : Encloses bp bpv) (hbl : Encloses bl blv) :
    0 < apv * alv ∧ 0 < bpv * blv ∧ bcv * (apv * alv) < acv * (bpv * blv) :=
  check_sound hcheck hac (mul_sound hap hal) hbc (mul_sound hbp hbl)

-- Per-prefix contribution bounds remain valid after summing disjoint completions.
theorem repeated_bounds {i : Interval} {xs : List Nat}
    (h : ∀ x ∈ xs, Encloses i x) :
    i.lo * xs.length ≤ sumValues xs ∧ sumValues xs ≤ i.hi * xs.length := by
  induction xs with
  | nil => simp [sumValues]
  | cons x xs ih =>
    have hx := h x (by simp)
    have ht := ih (by intro y hy; exact h y (by simp [hy]))
    simpa [sumValues, Nat.mul_succ, Nat.add_comm] using
      And.intro (Nat.add_le_add hx.1 ht.1) (Nat.add_le_add hx.2 ht.2)

end CertifiedRank

#print axioms CertifiedRank.check_sound
#print axioms CertifiedRank.add_sound
#print axioms CertifiedRank.mul_sound
#print axioms CertifiedRank.sum_sound
#print axioms CertifiedRank.product_sound
#print axioms CertifiedRank.three_state_sound
#print axioms CertifiedRank.three_state_rank_sound
#print axioms CertifiedRank.repeated_bounds
