"""Apply single source mutations in memory and require real audit assertions to fail."""

from pathlib import Path
import sys
import types

import audit


MUTATIONS = [
    ("nonstrict-rank", "checker_checks", "> b.numerator_upper * a.denominator_upper",
     ">= b.numerator_upper * a.denominator_upper"),
    ("upper-as-lower", "checker_checks", "a.numerator_lower * b.denominator_lower",
     "a.numerator_upper * b.denominator_lower"),
    ("swapped-denominator", "checker_checks", "a.numerator_lower * b.denominator_lower",
     "a.numerator_lower * a.denominator_upper"),
    ("noninteger-endpoints", "checker_checks", "all(type(v) is int for v in self.endpoints())",
     "True"),
    ("restart-generation", "cache_checks", "ticket.generation != self.generation or ", ""),
    ("replay-revision", "cache_checks", "or ticket.revision != current[0]", "or False"),
    ("producer-identity", "cache_checks", "result_key != ticket.key or ", ""),
    ("nested-enclosures", "cache_checks", "if not old_lower <= lower <= upper <= old_upper:",
     "if False:"),
    ("model-content-key", "controller_checks", "return self._key",
     "return self.n, ()"),
    ("singleton-invalid-denominator", "controller_checks", "if not ratio.valid():", "if False:"),
    ("prefix-upper", "producer_checks", "high *= b", "high *= a"),
    ("prefix-completion-count", "producer_checks", "return low * completions, high * completions",
     "return low, high"),
]


def main():
    source = Path(audit.core.__file__).read_text()
    original = audit.core
    print("| Source mutation | Independent assertion rejects it |")
    print("|---|---|")
    for label, check, before, after in MUTATIONS:
        assert source.count(before) == 1, (label, "mutation no longer uniquely matches source")
        module = types.ModuleType("campaign6_mutant_core")
        sys.modules[module.__name__] = module
        exec(compile(source.replace(before, after), "<campaign6_mutant_core>", "exec"), module.__dict__)
        audit.core = module
        try:
            getattr(audit, check)()
        except AssertionError:
            print(f"| {label} | yes |")
        else:
            raise AssertionError(f"surviving mutant: {label}")
        finally:
            audit.core = original
    print(f"\nmutants={len(MUTATIONS)} rejected={len(MUTATIONS)} survivors=0")


if __name__ == "__main__":
    main()
