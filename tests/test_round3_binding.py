import json
from pathlib import Path

import jsonschema

from scripts.bind_round3_amendment import ROOT, selection_rule


def test_all_required_selection_fields_bind_unchanged_cohort():
    schema = json.loads((ROOT / "grader/campaign-003/manifest.schema.json").read_text())
    rule = selection_rule()
    jsonschema.validate(rule, {"$defs": schema["$defs"], **schema["properties"]["selection_rule"]})
    assert rule["intended_cells"][0]["models"] == rule["intended_cells"][1]["models"] == 6
    assert "not measured" in rule["baseline_42_mapping_scope"]
    assert (ROOT / rule["baseline_42_mapping"]["path"]).is_file()
