"""Independent Decimal references, with explicit post-exposure audit selection."""

from datetime import datetime, timezone
from decimal import Decimal, localcontext
import itertools
import json
import math
from pathlib import Path
import time

from audit_semantics import factors

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "grader/campaign-002"


def read(path):
    return json.loads((ROOT / path).read_text())


def synthetic_reference(data):
    n = len(data["domains"])
    q = data["domains"][0]
    family = data["metadata"]["family"]
    x = Decimal(-1).exp()
    if family == "independent":
        return n * sum(Decimal(-v).exp() for v in range(q)).ln()
    if family == "chain":
        return Decimal(q).ln() + (n-1)*(1+(q-1)*x).ln()
    if family == "cycle":
        return ((1+(q-1)*x)**n + (q-1)*(1-x)**n).ln()
    if family == "constant":
        return n*Decimal(q).ln()
    if family == "separable":
        return n*sum(Decimal(-(n-1)*v).exp() for v in range(q)).ln()
    if family == "clique":
        z = Decimal(0)
        for prefix in itertools.product(range(n+1), repeat=q-1):
            if sum(prefix)>n:
                continue
            counts = prefix+(n-sum(prefix),)
            coefficient = math.factorial(n)//math.prod(math.factorial(k) for k in counts)
            unlike = sum(counts[i]*counts[j] for i in range(q) for j in range(i+1,q))
            z += coefficient*Decimal(-unlike).exp()
        return z.ln()
    if family == "grid4":
        states = list(itertools.product(range(q), repeat=4))
        internal = [sum(s[i]!=s[i+1] for i in range(3)) for s in states]
        table = [Decimal(-i).exp() for i in range(8)]
        mass = [table[e] for e in internal]
        for _ in range(3):
            following = []
            for j, to in enumerate(states):
                following.append(sum(weight*table[internal[j]+sum(a!=b for a,b in zip(fr,to))]
                                     for fr,weight in zip(states,mass)))
            mass = following
        return sum(mass).ln()
    return None


def enumerate_reference(data):
    """Sum exact binary64 log values using Decimal and hard-zero-only pruning."""
    domains = data["domains"]
    unary = [[Decimal(0) for _ in range(q)] for q in domains]
    pairs = {}
    scalar = Decimal(0)
    for scope, values in factors(data):
        d = [None if float(x) == -math.inf else Decimal.from_float(float(x)) for x in values.flat]
        if not scope:
            if d[0] is None:
                return {"log_z": "-Infinity", "positive_support_assignments": 0}
            scalar += d[0]
        elif len(scope)==1:
            i = scope[0]
            unary[i] = [None if a is None or b is None else a+b for a,b in zip(unary[i],d)]
        else:
            i,j = scope
            assert i<j
            if (i,j) not in pairs:
                pairs[(i,j)] = d
            else:
                pairs[(i,j)] = [None if a is None or b is None else a+b for a,b in zip(pairs[(i,j)],d)]
    allowed = [{a for a,x in enumerate(row) if x is not None} for row in unary]
    unary_support_count = math.prod(map(len,allowed))
    changed = True
    while changed:
        changed = False
        for (i,j), values in pairs.items():
            ai = {a for a in allowed[i] if any(values[a*domains[j]+b] is not None for b in allowed[j])}
            bj = {b for b in allowed[j] if any(values[a*domains[j]+b] is not None for a in allowed[i])}
            if ai!=allowed[i] or bj!=allowed[j]:
                changed=True
                allowed[i],allowed[j]=ai,bj
    if any(not x for x in allowed):
        return {"log_z": "-Infinity", "positive_support_assignments": 0,
                "declared_assignments": str(math.prod(domains)), "unary_supported_assignments": str(unary_support_count)}
    fixed = {i: next(iter(a)) for i,a in enumerate(allowed) if len(a)==1}
    active = sorted(set(range(len(domains)))-fixed.keys(), key=lambda i: (len(allowed[i]),i))
    for i,a in fixed.items():
        scalar += unary[i][a]
    for (i,j), values in pairs.items():
        if i in fixed and j in fixed:
            scalar += values[fixed[i]*domains[j]+fixed[j]]
        elif i in fixed:
            for b in allowed[j]:
                value=values[fixed[i]*domains[j]+b]
                assert value is not None
                unary[j][b] += value
        elif j in fixed:
            for a in allowed[i]:
                value=values[a*domains[j]+fixed[j]]
                assert value is not None
                unary[i][a] += value
    def weights():
        assigned = {}
        def visit(depth, weight):
            if depth==len(active):
                yield weight
                return
            i = active[depth]
            for a in sorted(allowed[i]):
                delta = unary[i][a]
                for j,b in assigned.items():
                    key=(min(i,j),max(i,j))
                    if key not in pairs:
                        continue
                    entry=pairs[key][a*domains[j]+b] if i<j else pairs[key][b*domains[i]+a]
                    if entry is None:
                        delta=None
                        break
                    delta += entry
                if delta is None:
                    continue
                assigned[i]=a
                yield from visit(depth+1,weight+delta)
                del assigned[i]
        yield from visit(0,scalar)
    maximum=None
    support=0
    for value in weights():
        support += 1
        maximum=value if maximum is None or value>maximum else maximum
    if maximum is None:
        return {"log_z":"-Infinity","positive_support_assignments":0}
    mass=Decimal(0)
    dropped=0
    for value in weights():
        if value-maximum < -300:
            dropped += 1
        else:
            mass += (value-maximum).exp()
    relative_tail_bound=Decimal(dropped)*Decimal(-300).exp()/mass
    return {"log_z":str(maximum+mass.ln()), "declared_assignments":str(math.prod(domains)),
            "unary_supported_assignments":str(unary_support_count),
            "arc_consistent_assignments":str(math.prod(map(len,allowed))),
            "positive_support_assignments":support, "fixed_after_zero_pruning":len(fixed),
            "tail_terms_below_maximum_minus_300":dropped,
            "analytic_relative_omitted_tail_bound_diagnostic":str(relative_tail_bound),
            "assurance":"90-digit Decimal, exact binary64 inputs and hard-zero-only support pruning. Exponentially negligible tail has an explicit count bound; arithmetic is not outward-rounded, so no strict interval certificate is asserted."}


def main():
    manifest=read("runs/campaign-002/manifest.json")
    result={"recorded_at_utc":datetime.now(timezone.utc).isoformat(), "precision_digits":90,
        "selection_exposure":"Post-exposure independent audit, not a prospective oracle or a campaign trial replacement. Synthetic cases are all10 with frozen references. Real checks select minimum baseline configuration count, largest baseline count <=100000, smallest finite stored baseline entry if enumerable <=100000, and1FYN as the statically smallest extension.",
        "synthetic":[],"real":[]}
    with localcontext() as ctx:
        ctx.prec=90
        for case in manifest["models"]:
            if case["cohort"]!="synthetic_measured":
                continue
            data=read(case["representations"][0]["files"][0]["path"])
            value=synthetic_reference(data)
            if value is None:
                continue
            reference=manifest["references"][case["model_id"]]
            error=abs(value-Decimal(reference["log_z"]))
            assert error<Decimal("1e-70")
            result["synthetic"].append({"model_id":case["model_id"],"log_z":str(value),"frozen_reference_absolute_error":str(error)})
        baseline=[x for x in manifest["models"] if x["cohort"]=="original_42"]
        statecount=lambda x:math.prod(x["representations"][0]["structure"]["domain_cardinalities"])
        baseline_small=[x for x in baseline if statecount(x)<=100000]
        smallest=min(baseline,key=statecount)
        largest=max(baseline_small,key=statecount)
        def minimum_entry(case):
            data=read(case["representations"][0]["files"][0]["path"])
            return min(float(v) for _,a in factors(data) for v in a.flat if math.isfinite(float(v)))
        extreme=min(baseline,key=minimum_entry)
        selected={x["model_id"]:x for x in [smallest,largest]+([extreme] if statecount(extreme)<=100000 else [])}
        selected.update({x["model_id"]:x for x in manifest["models"] if x["model_id"].startswith("1FYN__")})
        for case in selected.values():
            started=time.perf_counter()
            data=read(case["representations"][0]["files"][0]["path"])
            row=enumerate_reference(data)
            row["model_id"]=case["model_id"]
            row["audit_elapsed_seconds"]=time.perf_counter()-started
            ref=manifest["references"].get(case["model_id"])
            if ref and row["log_z"]!="-Infinity":
                row["frozen_reference_absolute_error"]=str(abs(Decimal(row["log_z"])-Decimal(str(ref["log_z"]))))
            trials=[json.loads(l) for l in (ROOT/"runs/campaign-002/trials.jsonl").read_text().splitlines()]
            row["original_completed_comparisons"]=[{"trial_id":t["trial_id"],"method":t["method_id"],"representation":t["representation_id"],"absolute_log_error":str(abs(Decimal.from_float(t["output"]["log_z"])-Decimal(row["log_z"])))} for t in trials if t["model_id"]==case["model_id"] and t["status"] in ["success","unverified_accuracy"] and isinstance(t["output"]["log_z"],(float,int))]
            result["real"].append(row)
            print(case["model_id"],row["positive_support_assignments"],row["audit_elapsed_seconds"],flush=True)
            (OUT/"independent_numeric_audit.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    (OUT/"independent_numeric_audit.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    main()
