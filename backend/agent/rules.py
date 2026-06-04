"""Rule versioning and management for the reconciliation agent."""

from backend.models.schemas import RuleSet

# Global rule registry
# v0: overly strict — causes uncertain/wrong decisions on edge cases (demo baseline)
# v1: sensible defaults — the "genuine improvement" target
_RULES: dict[str, RuleSet] = {
    "v0": RuleSet(
        version="v0",
        name_similarity_threshold=0.95,   # too strict — rejects similar names
        amount_tolerance_abs=2000.0,       # too tight — rejects bank-fee cases
        amount_tolerance_pct=0.005,
        date_tolerance_days=1,             # too tight — rejects 2-3 day difference
        min_confidence=0.9,               # too high — many uncertain results
    ),
    "v1": RuleSet(
        version="v1",
        name_similarity_threshold=0.7,
        amount_tolerance_abs=10000.0,
        amount_tolerance_pct=0.02,
        date_tolerance_days=5,
        min_confidence=0.6,
    ),
    # Reward-hacking demo: greedy rules that overfit train by accepting almost anything
    "v_greedy": RuleSet(
        version="v_greedy",
        name_similarity_threshold=0.0,
        amount_tolerance_abs=999_999_999.0,
        amount_tolerance_pct=1.0,
        date_tolerance_days=365,
        min_confidence=0.0,
    ),
}

_CURRENT_VERSION = "v1"


def get_current_rules() -> RuleSet:
    return _RULES[_CURRENT_VERSION]


def get_rules(version: str) -> RuleSet:
    return _RULES[version]


def get_current_version() -> str:
    return _CURRENT_VERSION


def register_rules(ruleset: RuleSet) -> None:
    _RULES[ruleset.version] = ruleset


def apply_rule_proposal(proposal, base_version: str = None) -> RuleSet:
    """Create a new RuleSet from a proposal by applying changes to the current rules."""
    base = _RULES[base_version] if base_version else get_current_rules()
    data = base.model_dump()

    for change in proposal.changes:
        # change format: "parameter=value"
        if "=" in change:
            key, val = change.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in data:
                try:
                    data[key] = type(data[key])(val)
                except (ValueError, TypeError):
                    pass

    data["version"] = proposal.rule_version
    return RuleSet(**data)


def set_current_version(version: str) -> None:
    global _CURRENT_VERSION
    if version not in _RULES:
        raise ValueError(f"Rule version {version} not registered")
    _CURRENT_VERSION = version


def list_versions() -> list[str]:
    return list(_RULES.keys())
