"""Seal the source audit, independent references and complete ranking pilot."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = ROOT/"runs/campaign-004"
    manifest = json.loads((run/"manifest.json").read_text())
    summary = json.loads((run/"summary.json").read_text())
    assert summary["panels"] == 12 and summary["planned_queries"] == 252 and summary["planned_state_slots"] == 756
    files = {Path(__file__).resolve()}
    prior_path = ROOT/"runs/campaign-003-review/bundle_manifest.json"
    prior = json.loads(prior_path.read_text())
    for item in prior["files"] + manifest["file_inventory"]:
        path = ROOT/item["path"]
        assert digest(path) == item["sha256"],item["path"]
        files.add(path)
    files.add(prior_path)
    old_audit_path = ROOT/"grader/campaign-003/AUDIT_SEAL.json"
    old_audit = json.loads(old_audit_path.read_text())
    for item in old_audit["files"]:
        assert digest(ROOT/item["path"]) == item["sha256"]
        files.add(ROOT/item["path"])
    files.add(old_audit_path)
    for directory in ["prepared/campaign-004","runs/campaign-004","grader/campaign-004","data/campaign-004/comparator_audit"]:
        files.update(path for path in (ROOT/directory).rglob("*") if path.is_file())
    review = ROOT/"runs/campaign-004-review"
    review.mkdir()
    claims = {"prepared_at_utc":datetime.now(timezone.utc).isoformat(),
        "execution_manifest_sha256":digest(run/"manifest.json"),
        "preparation_manifest_sha256":digest(ROOT/"prepared/campaign-004/preparation_manifest.json"),
        "summary":summary,
        "claims":[
            {"id":"source", "statement":"All14sourcecases have formalpost-freeze query/sum/metadata/factor audits and source-first baseline equivalence checks. The pilot is the predeclared minimum-sum case2rfe00012, all21source templates atF338, otherselectorsfixed. Histidineprotonationtemplates remain distinct; no index-based dummy/conformer exclusion."},
            {"id":"target", "statement":"The numerical target is represented unnormalized sourceweights expressed asstored binary64math.logfactors. Score=logZcomplex-logZprotein-logZligand when denominatorspositive; sourcezeros remain. This is a source-model score, not calibratedabsoluteaffinity or recoveredunroundedphysicalenergy."},
            {"id":"correctness", "statement":"All63conditionedtargets are independently checkedagainstoriginalsource entries, plus independentDecimal90/120 references forlexical/binary64source/storedlogtargets. All12measuredpanels report21reference-passing scores and top1/3/5compatiblewiththedeclaredreferenceenvelope. Grader must verify, includingstate/cacheidentityanduncertainty."},
            {"id":"coverage", "statement":"Both arms already finishall21templates under20s512MiB. This pilot demonstrates no additionalsequencecoverage fromGAC. All252query/756state identities including cachehits remain recorded; repeatsare not252independentvariants."},
            {"id":"costs", "statement":"Each freshworkerloadsoriginalarchiveonce; sharedstatecache is exactFP-basedwithorigins andsamepolicybotharms. Conditioning, transformations, hashchecks, inferenceandresultI/O arechargedwithincommonworkerclock. Controllerhash/referencevalidationisrecordedseparatelyinsidecampaigntotal. JudgeVE/batch tradeoffs without requiringpruningwin."},
            {"id":"ranking", "statement":"The modeledpanelrankhasbaselineLEUfirst, ARGsecond followedbyLYS/ASN/ILE; theLEU-ARGgap isabout0.0384naturallogunits. No variantbeatssourcebaselineinthispanel. Theseare computationalsource rankings, notexperimentalpredictions."},
            {"id":"comparators_and_biology", "statement":"Boundedofficialsourceauditfoundnovalidateddrop-inBBK/AOBB comparator; OSPREYrequiresunverifiedfixed-matrix adapter/confspace reconstruction. The2025experimental63-labeldatasetlackspreparedinputs/energytablesandsame-targetscoreoutputs inavailable supplement. Neitherdomain-solver superiority norbiologicalaccuracyisclaimed."},
            {"id":"scope", "statement":"No ETHimplementation, novelcountingalgorithm, portabletimingranking, or improvedbindingaffinityprediction. Allrawsources/preparation/stage failures/testlogs/artifacts preserved; no measuredtrialretry."}],
        "requested_review":"Independently verify allsource semantics/decomposition andconformerpolicy, numeric/mapping/exactpruning/source-zero invariants, references/conversiondifferences/rank margins, fullledgers/cacheprovenance/chronology/resourceclocks, comparator/biological limits. Reportcorrectness/cost/negativefindings withno preferredwinner; failedphysicalgate restrictsclaims toencodedscorediagnostics."}
    path = review/"claims.json"
    path.write_text(json.dumps(claims,indent=2)+"\n")
    files.add(path)
    bundle = {"frozen_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"All004scientificchoices/preparation/references/measurements andphase1grader criteria, plus immutable003evidence. Laterplots/reports/independentauditfiles separate.",
        "files":[{"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":digest(path)} for path in sorted(files)]}
    path = review/"bundle_manifest.json"
    path.write_text(json.dumps(bundle,indent=2)+"\n")
    (review/"bundle_manifest.sha256").write_text(digest(path)+"  bundle_manifest.json\n")
    print(json.dumps({"bundle":str(path.relative_to(ROOT)),"sha256_prefix":digest(path)[:6],"files":len(files)}))


if __name__ == "__main__":
    main()
