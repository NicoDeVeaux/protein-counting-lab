"""Capture every full-manifest schema error without launching a measured worker."""

import json
from pathlib import Path

import jsonschema

from scripts import campaign_round3 as driver

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / "runs/campaign-003-schema-diagnostic"


class Captured(Exception):
    pass


def inspect(name, payload):
    schema = json.loads((ROOT / "grader/campaign-003" / (name+".schema.json")).read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = [{"path": list(error.absolute_path), "message": error.message} for error in validator.iter_errors(payload)]
    (DIAGNOSTIC / "candidate.json").write_text(json.dumps(payload, indent=2) + "\n")
    (DIAGNOSTIC / "all-schema-errors.json").write_text(json.dumps(errors, indent=2) + "\n")
    print(json.dumps({"schema_errors": len(errors), "unique_messages": sorted({error["message"] for error in errors}),
                      "timed_workers_launched": 0}), flush=True)
    raise Captured()


if __name__ == "__main__":
    driver.validate = inspect
    try:
        driver.freeze(ROOT / "prepared/campaign-003/catalog.amendment-002.json", DIAGNOSTIC)
    except Captured:
        pass
