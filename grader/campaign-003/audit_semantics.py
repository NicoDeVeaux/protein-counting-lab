"""Replay support and exact factor identities from JSON, independently of experiment modules."""

from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import itertools
import json
import math
import struct
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read(p):
    return json.loads((ROOT/p).read_text())


def parse(d):
    domains = d['domains']
    factors = []
    for f in d.get('factors', []):
        scope = f['scope']
        raw = np.asarray(f['log_values'], dtype=object)
        values = np.array([-math.inf if v is None or v == '-inf' else float(v) for v in raw.flat], dtype=np.float64)
        values = values.reshape(tuple(domains[v] for v in scope))
        assert not np.isnan(values).any() and not np.isposinf(values).any()
        factors.append((scope, values))
    if 'constant_log_weight' in d:
        v = d['constant_log_weight']
        factors.append(([], np.array(-math.inf if v is None else float(v))))
    return domains, factors


def fingerprint(domains, factors):
    h = hashlib.sha256(b'campaign003-numerical-target-v1\0')
    def ints(xs):
        h.update(struct.pack('>Q', len(xs)))
        for x in xs: h.update(struct.pack('>Q', x))
    ints(domains)
    h.update(struct.pack('>Q',len(factors)))
    for scope, values in factors:
        ints(scope); ints(values.shape); h.update(np.asarray(values,dtype='<f8').tobytes())
    return h.hexdigest()


def constraint_sets(domains, factors):
    groups = defaultdict(list)
    scalar_zeros = []
    for i,(scope, values) in enumerate(factors):
        if scope: groups[tuple(sorted(scope))].append(i)
        elif float(values) == -math.inf: scalar_zeros.append(i)
    constraints=[]
    for scope, indices in sorted(groups.items()):
        allowed=set()
        for a in itertools.product(*(range(domains[v]) for v in scope)):
            assignment=dict(zip(scope,a))
            if all(float(factors[i][1][tuple(assignment[v] for v in factors[i][0])]) != -math.inf for i in indices):
                allowed.add(a)
        constraints.append((scope,indices,allowed))
    return constraints,scalar_zeros


def replay(domains, factors, ledger):
    constraints, scalar_zeros=constraint_sets(domains,factors)
    assert ledger['input_domains']==domains
    active=[list(range(q)) for q in domains]
    for c,record in zip(constraints,ledger['constraints']):
        scope,indices,allowed=c
        assert list(scope)==record['scope'] and indices==record['source_factor_indices']
        entries=math.prod(domains[v] for v in scope)
        assert entries==record['entries']
        assert entries-len(allowed)==record['hard_zero_entries_after_scope_intersection']
    assert len(constraints)==len(ledger['constraints'])
    for event in ledger['deletions']:
        scope,indices,allowed=constraints[event['constraint_index']]
        assert list(scope)==event['scope'] and indices==event['source_factor_indices']
        assert event['allowed_before']=={str(v):active[v] for v in scope}
        live=[a for a in allowed if all(a[j] in active[v] for j,v in enumerate(scope))]
        expected={str(v):[x for x in active[v] if not any(a[j]==x for a in live)] for j,v in enumerate(scope)}
        expected={k:v for k,v in expected.items() if v}
        assert expected==event['removed_original_indices']
        for k,values in expected.items(): active[int(k)]=[v for v in active[int(k)] if v not in values]
    assert active==ledger['retained_original_indices']
    assert str(math.prod(map(len,active)))==ledger['retained_cartesian_assignments']
    assert sum(q-len(a) for q,a in zip(domains,active))==ledger['removed_domain_values']
    if ledger['status']=='proven_zero':
        reason=ledger['inconsistency_proof']
        if reason['kind']=='scalar_hard_zero': assert scalar_zeros==reason['source_factor_indices']
        else:
            assert reason['kind']=='domain_wipeout' and any(not a for a in active)
            assert reason['trace_event_index']==len(ledger['deletions'])-1
        assert ledger['output_domains']==[1]*len(domains)
        return [1]*len(domains),[([],np.array(-math.inf))]
    assert not scalar_zeros and all(active)
    for scope,_,allowed in constraints:
        live=[a for a in allowed if all(a[j] in active[v] for j,v in enumerate(scope))]
        assert all(any(a[j]==x for a in live) for j,v in enumerate(scope) for x in active[v])
    # Reverse-order sweep independently checks the same unique nonzero fixed point.
    independent=[set(range(q)) for q in domains]
    changed=True
    while changed:
        changed=False
        for scope,_,allowed in reversed(constraints):
            live=[a for a in allowed if all(a[j] in independent[v] for j,v in enumerate(scope))]
            for j,v in enumerate(scope):
                new=independent[v] & {a[j] for a in live}
                changed |= new!=independent[v]
                independent[v]=new
    assert [sorted(x) for x in independent]==active
    assert ledger['output_value_original_indices']==active
    sliced=[]
    assert len(ledger['factor_restrictions'])==len(factors)
    for i,((scope,values),record) in enumerate(zip(factors,ledger['factor_restrictions'])):
        assert record['input_factor_index']==i and record['scope']==scope
        assert record['input_shape']==list(values.shape)
        assert record['original_indices_per_axis']==[active[v] for v in scope]
        assert record['restricted_shape']==[len(active[v]) for v in scope]
        assert record['restricted_factor_index_before_algebra']==i
        new=values[np.ix_(*(active[v] for v in scope))] if scope else values.copy()
        sliced.append((scope,new))
    return list(map(len,active)),sliced


def algebra(source, output, transformations):
    indexed={t['source_factor_index']:t for t in transformations}
    assert len(indexed)==len(transformations)
    cursor=0
    entries=0
    for i,(scope,values) in enumerate(source):
        t=indexed.get(i)
        replacement=output[cursor:cursor+(len(t['new_scopes']) if t else 1)]
        cursor+=len(replacement)
        if t:
            assert t['old_scope']==scope and [f[0] for f in replacement]==t['new_scopes']
            assert t['kind'] in {'constant_factor','independent_of_first_axis','independent_of_second_axis','exact_binary_rational_additive_split'}
        else:
            assert len(replacement)==1 and replacement[0][0]==scope
            assert replacement[0][1].tobytes()==values.tobytes()
        assert all(set(s)<=set(scope) for s,_ in replacement)
        for idx in np.ndindex(values.shape):
            assignment=dict(zip(scope,idx))
            old=float(values[idx])
            terms=[float(v[tuple(assignment[x] for x in s)]) for s,v in replacement]
            if old==-math.inf: assert -math.inf in terms
            else: assert all(math.isfinite(x) for x in terms) and sum(map(Fraction,terms),Fraction())==Fraction(old)
            entries+=1
    assert cursor==len(output)
    return entries


def structure(domains,factors,record):
    assert record['domain_cardinalities']==domains
    assert record['variables']==len(domains)
    assert record['nontrivial_variables']==sum(q>1 for q in domains)
    assert record['factor_scopes']==[s for s,_ in factors]
    assert record['factor_entries']==[v.size for _,v in factors]
    neighbors={v:set() for v in range(len(domains))}
    edges=set()
    for scope,_ in factors:
        for x,y in itertools.combinations(scope,2):
            neighbors[x].add(y);neighbors[y].add(x);edges.add(tuple(sorted((x,y))))
    assert record['primal_edges']==len(edges)
    visited=set();components=0
    for v in neighbors:
        if v in visited:continue
        components+=1;stack=[v]
        while stack:
            u=stack.pop()
            if u not in visited:visited.add(u);stack.extend(neighbors[u]-visited)
    assert record['components']==components
    peak=1;width=0
    for v in record['elimination_order']:
        adjacent=neighbors.pop(v)
        peak=max(peak,math.prod(domains[x] for x in adjacent|{v}))
        width=max(width,len(adjacent))
        for u in adjacent:
            neighbors[u].discard(v);neighbors[u].update(adjacent-{u})
    assert not neighbors and width==record['induced_width']
    assert peak==record['predicted_largest_intermediate_entries']
    assert 8*peak==record['predicted_largest_intermediate_bytes']
    return {'variables':len(domains),'nontrivial':sum(q>1 for q in domains),'domains':domains,'cartesian_assignments':str(math.prod(domains)), 'factor_entries':sum(v.size for _,v in factors),'edges':len(edges),'largest_recorded_order_table_bytes':8*peak}


def decimal_partition(domains,factors):
    energies=Counter()
    for assignment in itertools.product(*(range(q) for q in domains)):
        terms=[float(values[tuple(assignment[v] for v in scope)]) for scope,values in factors]
        if -math.inf in terms:continue
        energies[sum(map(Fraction,terms),Fraction())]+=1
    if not energies:return '-Infinity',0
    with localcontext() as ctx:
        ctx.prec=90
        maximum=max(energies)
        mass=Decimal(0)
        for energy,count in energies.items():
            diff=energy-maximum
            mass+=Decimal(count)*(Decimal(diff.numerator)/Decimal(diff.denominator)).exp()
        answer=Decimal(maximum.numerator)/Decimal(maximum.denominator)+mass.ln()
        return str(answer),sum(energies.values())


def audit():
    manifest=read('runs/campaign-003-amendment-003/manifest.json')
    checked=[];controls=[];allentries=0
    for m in manifest['models']:
        original=read(m['pipeline_input']['path'])
        domains,factors=parse(original)
        record={'model_id':m['model_id'],'cohort':m['cohort'],'input_domains':domains,'input_cartesian_assignments':str(math.prod(domains)), 'input_factor_entries':sum(v.size for _,v in factors),'arms':{}}
        if m['cohort']=='synthetic_measured':
            answer,positive=decimal_partition(domains,factors)
            reference=manifest['references'][m['model_id']]['log_z']
            if answer=='-Infinity': assert reference in ['-Infinity','-inf']
            else: assert abs(Decimal(answer)-Decimal(str(reference)))<Decimal('1e-70')
            controls.append({'model_id':m['model_id'],'independent_decimal90_log_z':answer,'positive_support_assignments':positive,'declared_reference':reference,'finite_tail_note':'Positive tails retained in support. Decimal90 rounds 8*log(1+exp(-1000)) to 0; exact value is positive and at most 8*exp(-1000).' if m['model_id']=='control003-finite-tail' else None})
        for rep in m['representations']:
            arm=rep['representation_id']
            proof=read('prepared/campaign-003/proofs/'+m['model_id']+'__'+arm+'.json')
            pd=proof['pipeline']
            if arm=='propagated':
                rd,rf=replay(domains,factors,pd['propagation_proof'])
            else:
                assert pd['propagation_proof'] is None
                rd,rf=domains,factors
            derived=parse(read(rep['files'][0]['path']))
            assert derived[0]==rd==proof['output_domains']
            assert fingerprint(*derived)==rep['target_sha256']==pd['target_sha256']
            allentries+=algebra(rf,derived[1],pd['algebra_transformations'])
            summary=structure(*derived,rep['structure'])
            summary['exact_transformations']=len(pd['algebra_transformations'])
            if arm=='propagated':
                p=pd['propagation_proof']
                summary.update({'support_status':p['status'],'removed_domain_values':p['removed_domain_values'],'deletion_events':len(p['deletions']),'retained_original_indices':p['retained_original_indices']})
            if m['cohort']=='synthetic_measured':
                dz,dp=decimal_partition(*derived)
                assert dz==answer or (dz!='-Infinity' and answer!='-Infinity' and abs(Decimal(dz)-Decimal(answer))<Decimal('1e-70'))
                if pd['propagation_proof'] and pd['propagation_proof']['status']=='proven_zero':assert positive==0
            record['arms'][arm]=summary
        checked.append(record)
    rows=[json.loads(x) for x in (ROOT/'runs/campaign-003-amendment-003/trials.jsonl').read_text().splitlines()]
    errors=[];validated=0;exactzeros=0
    for row in rows:
        if row['status']!='success':continue
        raw=read(row['output']['artifact']['path'])
        reference=manifest['references'][row['model_id']]
        value=row['output']['log_z']; target=reference['log_z']
        v=-math.inf if value in ['-Infinity','-inf'] else float(value)
        z=-math.inf if target in ['-Infinity','-inf'] else float(target)
        assert (v==-math.inf)==(z==-math.inf)
        metrics=raw.get('metrics',{})
        magnitude=abs(metrics.get('scalar_log_offset',0))+math.fsum(abs(x.get('log_offset',0)) for x in metrics.get('factor_conversion',[]))
        threshold=1e-8+64*sys.float_info.epsilon*max(1,abs(z) if math.isfinite(z) else 1,magnitude)
        if v==-math.inf:error=0;exactzeros+=1
        else:
            with localcontext() as ctx:
                ctx.prec=110
                exactreference=Decimal(target) if isinstance(target,str) else Decimal.from_float(target)
                error=float(abs(Decimal.from_float(v)-exactreference))
        assert error<=threshold
        assert threshold==row['validation']['acceptance_threshold']
        assert error==row['validation']['absolute_log_error']
        errors.append(error);validated+=1
    result={'all_representations_checked':len(checked)*2,'models':checked,'exact_factor_entry_identities_checked':allentries,'independent_decimal90_controls':controls,'reference_successes_recompared':validated,'exact_zero_successes':exactzeros,'max_absolute_log_error':max(errors),'fresh_protein_oracles_created':False,'protein_reference_scope':'Prior independently computed campaign002 1FYN Decimal90 value reused prospectively; no new oracle for the other five.','independence':'No experiment module imported. JSON support sets/trace replay, reverse-order fixed-point verification, exact Fraction factor identities, graph/order estimates and Decimal enumeration are grader code.','limits':['Not an outward-rounded interval certificate.','Fresh Decimal enumeration is confined to all six bounded measured controls; prior 1FYN evidence reused.','Frozen random unit controls use exact assignment-weight checks and a binary64 sum check; their source/retained preflight record is inspected, not rerun by importing preprocessing.']}
    (OUT/'semantics_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'representations':result['all_representations_checked'],'factor_entries':allentries,'successes':validated,'max_error':max(errors),'proteins':[{k:v for k,v in r.items() if k in ['model_id','input_cartesian_assignments','arms']} for r in checked if r['cohort']=='published_protein_extension']},indent=2))


if __name__=='__main__':
    audit()
