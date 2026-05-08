"""
Clinical audit runner — dispatches to the appropriate agent module.

Entry point: strength_app/management/commands/clinical_audit.py
"""

from __future__ import annotations

AGENT_REGISTRY = {
    "orchestrator_selftest": "_selftest",
    "1_strength_gen": "generators.strength_generator",
    "2_football_gen": "generators.football_generator",
    "3_adversarial_gen": "generators.adversarial_generator",
    "4_football_scoring_oracle": "oracles.football_scoring_oracle",
    "5_football_prescription_oracle": "oracles.football_prescription_oracle",
    "6_strength_prescription_oracle": "oracles.strength_prescription_oracle",
    "7_coverage_watcher": "watchers.coverage_watcher",
    "8_oracle_consistency_watcher": "watchers.oracle_consistency_watcher",
    "9_safety_watcher": "watchers.safety_invariant_watcher",
}

_BASE = "strength_app.tests.clinical_audit"


def run(agent_id: str, n: int, seed: int, against_cases: str, read: str, **kwargs) -> int:
    """Dispatch to the named agent. Returns exit code (0 = success)."""
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent {agent_id!r}. Known agents: {list(AGENT_REGISTRY)}"
        )

    module_name = AGENT_REGISTRY[agent_id]

    if module_name == "_selftest":
        return _selftest()

    import importlib
    module = importlib.import_module(f"{_BASE}.{module_name}")

    if not hasattr(module, "audit_run"):
        raise NotImplementedError(
            f"Agent module {module_name!r} does not yet implement audit_run(). "
            "This stub will be filled in by the responsible agent."
        )

    return module.audit_run(
        n=n,
        seed=seed,
        against_cases=against_cases,
        read=read,
        **kwargs,
    )


def _selftest() -> int:
    """Verify all scaffold imports work. Returns 0 on success, raises on failure."""
    from strength_app.tests.clinical_audit.core.patient_case import (
        SyntheticPatientCase, invariant_decorator,
    )
    from strength_app.tests.clinical_audit.core.finding import Finding

    # Smoke-test SyntheticPatientCase construction
    case = SyntheticPatientCase.build(
        case_kind="strength",
        age=30,
        sex="M",
        height_cm=178.0,
        weight_kg=80.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
    )
    assert case.case_id, "case_id must be non-empty"
    assert case.hash() == case.case_id, "hash() must match case_id"

    # Determinism: same inputs → same case_id
    case2 = SyntheticPatientCase.build(
        case_kind="strength",
        age=30,
        sex="M",
        height_cm=178.0,
        weight_kg=80.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
    )
    assert case.case_id == case2.case_id, "case_id must be deterministic"

    # Smoke-test Finding construction
    f = Finding(
        severity="HIGH",
        agent_id="selftest",
        category="test",
        title="Self-test finding",
        description="Generated during orchestrator selftest.",
        reproduction="See _selftest() in runner.py",
        suggested_fix="N/A",
        clinical_rationale="N/A",
        case_id=case.case_id,
    )
    assert f.severity_rank() == 1

    # Smoke-test invariant_decorator
    from strength_app.tests.clinical_audit.core.patient_case import invariant_decorator

    @invariant_decorator("CRITICAL", "test_invariant", "selftest rationale")
    def _dummy_invariant(c, out):
        return None

    assert _dummy_invariant(case, {}) is None

    # Verify agent modules are importable (stubs — no audit_run yet)
    import importlib
    for agent_id, module_name in AGENT_REGISTRY.items():
        if module_name == "_selftest":
            continue
        try:
            importlib.import_module(f"{_BASE}.{module_name}")
        except ImportError as e:
            raise ImportError(f"Cannot import agent module {module_name!r}: {e}") from e

    print("orchestrator_selftest: ALL IMPORTS OK — scaffold is functional")
    return 0
