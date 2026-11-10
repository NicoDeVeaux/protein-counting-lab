"""Reaggregate complete paired costs, censoring and schedule/phase dispersion."""

from pathlib import Path
from collections import Counter,defaultdict
import json
import math
import random
import statistics

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def summary(xs):
    xs=[x for x in xs if x is not None]
    return {'n':len(xs),'min':min(xs),'median':statistics.median(xs),'max':max(xs)} if xs else None


def audit():
    manifest=json.loads((ROOT/'runs/campaign-003-amendment-003/manifest.json').read_text())
    rows=[json.loads(x) for x in (ROOT/'runs/campaign-003-amendment-003/trials.jsonl').read_text().splitlines()]
    models={m['model_id']:m for m in manifest['models']}
    # Reconstruct the declared deterministic block schedule without importing its implementation.
    rng=random.Random(2026110603)
    blocks=[(m['model_id'],p) for m in sorted(manifest['models'],key=lambda m:m['model_id']) for p in sorted(m['representations'][0]['resource_profiles'])]
    rebuilt=[]
    for repeat in range(3):
        shuffled=blocks.copy();rng.shuffle(shuffled)
        for model,profile in shuffled:
            methods=['ve','batch','pyagrum'];rng.shuffle(methods)
            for method in methods:
                arms=['simplified','propagated'];rng.shuffle(arms)
                for arm in arms:
                    rebuilt.append((model,profile,repeat,method,arm))
    actual=[(r['model_id'],r['resource_profile_id'],r['repeat'],r['method_id'],r['representation_id']) for r in rows]
    assert actual==rebuilt
    cells=defaultdict(list);outcomes=defaultdict(Counter)
    for r in rows:
        cells[(r['model_id'],r['method_id'],r['resource_profile_id'],r['representation_id'])].append(r)
        outcomes[(models[r['model_id']]['cohort'],r['method_id'],r['representation_id'])][r['status']]+=1
    cell_records=[]
    scopes=['loading','propagation','simplification','target_fingerprint','solver_call','inference_kernel','serialization']
    dispersion=defaultdict(list)
    repeat_trends=defaultdict(list)
    oneFYN=[]
    for key,rs in sorted(cells.items()):
        correct=[r for r in rs if r['status']=='success']
        record={'model_id':key[0],'method':key[1],'profile':key[2],'arm':key[3], 'outcomes':dict(Counter(r['status'] for r in rs)),'completed_correct':len(correct), 'wall_seconds':summary([r['timing']['wall_seconds'] for r in correct]),'cpu_seconds':summary([r['timing']['cpu_seconds'] for r in correct]),'whole_peak_rss_bytes':summary([max(r['memory']['rss_peak_bytes'] or 0,r['memory'].get('worker_reported_lifetime_peak_rss_bytes') or 0) for r in correct]),'phases':{p:summary([r['timing']['phases'].get(p) for r in correct]) for p in scopes}}
        if len(correct)==3:
            ordered=sorted(correct,key=lambda r:r['repeat'])
            for scope in ['wall','cpu']+scopes:
                values=[r['timing']['wall_seconds'] if scope=='wall' else r['timing']['cpu_seconds'] if scope=='cpu' else r['timing']['phases'].get(scope) for r in ordered]
                if all(x is not None and x>0 for x in values):
                    dispersion[scope].append(max(values)/min(values))
                    repeat_trends[scope].append(values[-1]/values[0])
        cell_records.append(record)
        if key[0].startswith('1FYN'):oneFYN.append(record)
    pairs=[]
    groups=defaultdict(dict)
    for r in rows:
        groups[(r['model_id'],r['method_id'],r['resource_profile_id'],r['repeat'])][r['representation_id']]=r
    arm_first=Counter()
    for key,pair in groups.items():
        assert set(pair)=={'simplified','propagated'}
        a,b=pair['simplified'],pair['propagated']
        assert abs(int(a['trial_id'])-int(b['trial_id']))==1
        arm_first['simplified' if int(a['trial_id'])<int(b['trial_id']) else 'propagated']+=1
        if a['status']!='success' or b['status']!='success':continue
        ratio=a['timing']['wall_seconds']/b['timing']['wall_seconds']
        ratios={'wall':ratio,'cpu':a['timing']['cpu_seconds']/b['timing']['cpu_seconds']}
        for phase in scopes:
            x,y=a['timing']['phases'].get(phase),b['timing']['phases'].get(phase)
            if x is not None and y is not None and y>0:ratios[phase]=x/y
        pairs.append({'model_id':key[0],'method':key[1],'profile':key[2],'repeat':key[3],'first_arm':'simplified' if int(a['trial_id'])<int(b['trial_id']) else 'propagated','simplified_trial':a['trial_id'],'propagated_trial':b['trial_id'],'baseline_over_propagated':ratios})
    protein_rows=[r for r in rows if models[r['model_id']]['cohort']=='published_protein_extension']
    byprotein={m['model_id']:{arm:dict(Counter(r['status'] for r in protein_rows if r['model_id']==m['model_id'] and r['representation_id']==arm)) for arm in ['simplified','propagated']} for m in manifest['models'] if m['cohort']=='published_protein_extension'}
    timeouts=[{'trial_id':r['trial_id'],'model_id':r['model_id'],'method':r['method_id'],'profile':r['resource_profile_id'],'arm':r['representation_id'],'repeat':r['repeat'],'wall_seconds':r['timing']['wall_seconds'],'right_censored':r['timing']['right_censored'],'reason':r['monitor']['termination_reason'],'trigger':r['monitor']['limit_trigger_seconds'],'kill':r['monitor']['kill_seconds']} for r in rows if r['status']=='timeout']
    result={'schedule_seed_reconstruction_matches':True,'adjacent_arm_pairs':len(groups),'first_arm_counts':dict(arm_first),'complete_correct_cells':sum(c['completed_correct']==3 for c in cell_records),'partial_correct_cells':sum(0<c['completed_correct']<3 for c in cell_records),'all_cells':cell_records,'oneFYN':oneFYN,'matched_correct_pairs':pairs,'outcomes_by_cohort_method_arm':[{'cohort':k[0],'method':k[1],'arm':k[2],'outcomes':dict(v)} for k,v in sorted(outcomes.items())],'protein_outcomes':byprotein,'repeat_max_min_dispersion':{k:summary(v) for k,v in dispersion.items()},'repeat2_over_repeat0':{k:summary(v) for k,v in repeat_trends.items()},'wall_dispersion_gt2':sum(v>2 for v in dispersion['wall']),'wall_dispersion_gt5':sum(v>5 for v in dispersion['wall']),'timeouts':timeouts,'system_load_average_range':{str(i):summary([r['system_load_average_at_start'][i] for r in rows]) for i in range(3)},'limits':['Ratios only compare correct completed matched rows; all failures/censoring retained separately.','Tiny kernel/phase timings have large relative noise; host-load telemetry is descriptive and does not establish drift cause.','Three repeats on a convenience cohort support local observed costs, not broad superiority, stable scaling or population inference.']}
    (OUT/'timing_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['first_arm_counts','complete_correct_cells','partial_correct_cells','repeat_max_min_dispersion','repeat2_over_repeat0','wall_dispersion_gt2','timeouts','protein_outcomes']},indent=2))


if __name__=='__main__':audit()
