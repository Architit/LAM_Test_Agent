from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _has(text: str, token: str) -> bool:
    return token in text


def _has_all(text: str, *tokens: str) -> bool:
    return all(token in text for token in tokens)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid json object: {path}")
    return data


def implemented_layers(repo_root: Path) -> set[str]:
    workflow = _read(repo_root / ".github" / "workflows" / "main.yml")
    live_policy = _read(repo_root / "lam_test_agent_live_policy.py")
    contracts_runtime = _read(repo_root / "lam_test_agent_contracts.py")
    route_matrix_runtime = _read(repo_root / "lam_test_agent_route_matrix.py")
    growth_data = _read(repo_root / "lam_test_agent_growth_data.py")
    backlog = _read(repo_root / "lam_test_agent_growth_backlog.py")
    gateway = _read(repo_root / "scripts" / "gateway_io.sh")
    matrix_sync = _read(repo_root / "lam_test_agent_matrix_sync.py")
    interaction = _read(repo_root / "INTERACTION_PROTOCOL.md")
    contracts_it = _read(repo_root / "tests" / "it" / "test_route_matrix_contracts.py")
    topology_it = _read(repo_root / "tests" / "it" / "test_route_matrix_failure_topology.py")

    found: set[str] = set()

    if _has(route_matrix_runtime, "def normalize_execution_payload") and _has_all(
        contracts_it, "normalize_execution_payload", "missing field: scenario_id"
    ):
        found.add("contract_schema_lock")
    if _has(route_matrix_runtime, "trace continuity violated across route hops") and _has(
        contracts_runtime, "is_valid_trace_id"
    ) and _has_all(contracts_it, "is_valid_trace_id", "trace_id") and _has(
        topology_it, "trace continuity violated across route hops"
    ):
        found.add("trace_continuity_guard")
    if _has(route_matrix_runtime, "status = spec.expected_status") and _has(
        contracts_it, "normalized.status == spec.expected_status"
    ):
        found.add("status_semantic_guard")
    if _has(route_matrix_runtime, 'reason = "provider_unavailable" if fallback_used else None') and _has_all(
        contracts_it, "normalized.fallback_used", 'normalized.reason == "provider_unavailable"'
    ) and _has(topology_it, "degraded status requires fallback_used=true"):
        found.add("fallback_determinism_guard")
    if _has(live_policy, "degraded_mode_conformance_gate") and _has(interaction, "degraded"):
        found.add("degraded_mode_conformance")

    if _has(gateway, "import_staging"):
        found.add("gateway_staging_only")
    if _has(gateway, "verify_github") and _has(gateway, "verify_onedrive"):
        found.add("gateway_reachability_probe")

    if _has(live_policy, "submodule_readiness_gate"):
        found.add("submodule_readiness_gate")
    if _has(live_policy, "network_resolution_gate"):
        found.add("network_resolution_gate")
    if _has(live_policy, "recommended_mode"):
        found.add("live_mode_activation_gate")
        found.add("mock_mode_fallback_gate")
    if _has(live_policy, "growth_checkpoint_gate"):
        found.add("growth_checkpoint_gate")
    if _has(live_policy, "archivator_handoff_gate"):
        found.add("archivator_handoff_gate")

    if _has(workflow, "Ruff") and _has(workflow, "Mypy"):
        found.add("ci_quality_gate")
    if _has(workflow, "--cov-fail-under=65"):
        found.add("runtime_coverage_gate")
    if _has(matrix_sync, "route_ids_from_matrix_file"):
        found.add("matrix_sync_gate")
    if _has(matrix_sync, "route_statuses_from_matrix_file"):
        found.add("matrix_status_sync_gate")
    if _has(workflow, "lam_test_agent_plan_guard --ecosystem") or _has(workflow, "lam_test_agent_deadloop_global_telemetry"):
        found.add("deadloop_global_scan")
    if _has(workflow, "lam_test_agent_growth_data"):
        found.add("growth_snapshot_gate")
    if _has(workflow, "lam_test_agent_growth_backlog"):
        found.add("bounded_backlog_gate")
    if _has(workflow, "lam_test_agent_growth_checkpoint_gate"):
        found.add("growth_checkpoint_artifact_gate")
    if _has(workflow, "lam_test_agent_telemetry_freshness_gate"):
        found.add("telemetry_freshness_gate")
    if _has(workflow, "lam_test_agent_telemetry_integrity_gate"):
        found.add("telemetry_integrity_gate")

    if _has(backlog, "max-total") or _has(backlog, "DEFAULT_MAX_TOTAL"):
        found.add("change_budget")
    if _has(backlog, "max-per-route") or _has(backlog, "DEFAULT_MAX_PER_ROUTE"):
        found.add("task_per_route_budget")
    if _has(backlog, "No recursive self-expansion"):
        found.add("no_recursive_generation")
    if _has(growth_data, "priority"):
        found.add("priority_ceiling_control")

    if _has(interaction, "governance tag"):
        found.add("governance_tagging_required")
    if _has(interaction, "ROADMAP.md") and _has(interaction, "DEV_LOGS.md"):
        found.add("roadmap_log_sync_gate")
    if _has(interaction, "operator_intervention_required"):
        found.add("operator_intervention_fallback")
    if _has(interaction, "release") or _has(interaction, "BLOCKED"):
        found.add("release_block_on_critical_gaps")

    return found


def unblock_conditions(policy: dict[str, Any]) -> list[str]:
    checks = policy.get("checks", [])
    out: list[str] = []
    for check in checks:
        if not isinstance(check, dict) or check.get("ok") is True:
            continue
        cid = check.get("id")
        if cid == "network_resolution_gate":
            out.append("Restore DNS/network resolution for github.com and re-run telemetry.")
        elif cid == "submodule_readiness_gate":
            out.append("Materialize required submodule src paths via bootstrap and verify live_ready=true.")
        elif cid == "dirty_repo_budget_gate":
            out.append("Reduce dirty repos to fit policy budget or raise budget through governance decision.")
        elif cid == "p0_gap_budget_gate":
            out.append("Burn down P0 live gaps or approve temporary P0 budget for staged rollout.")
        elif cid == "growth_checkpoint_gate":
            out.append("Regenerate growth snapshot with deadloop_cross_repo readiness block and re-run live policy.")
        elif cid == "archivator_handoff_gate":
            out.append("Refresh Archivator handoff mirrors (SubtreeHub/repos/*/WORKFLOW_SNAPSHOT_STATE.md) and re-run telemetry.")
        elif cid == "semantic_identity_governance_gate":
            out.append("Replace unresolved/provisional/template semantic triplets in SEMANTIC_IDENTITY_MAP* and re-run telemetry.")
    if not out:
        out.append("All policy gates currently pass.")
    return out


def build_drift_report(repo_root: Path, stack: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    layers = [str(layer.get("id")) for layer in stack.get("layers", []) if isinstance(layer, dict)]
    implemented = implemented_layers(repo_root)
    missing = sorted([lid for lid in layers if lid not in implemented])
    coverage = 0.0 if not layers else round((len(layers) - len(missing)) / len(layers) * 100.0, 2)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stack_layers_total": len(layers),
        "implemented_layers_count": len(layers) - len(missing),
        "implementation_coverage_percent": coverage,
        "missing_layers": missing,
        "live_policy_status": policy.get("status"),
        "live_recommended_mode": policy.get("recommended_mode"),
        "unblock_conditions": unblock_conditions(policy),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PHASE_E_DRIFT_REPORT",
        "",
        f"- generated_at_utc: {report['generated_at_utc']}",
        f"- stack_layers_total: {report['stack_layers_total']}",
        f"- implemented_layers_count: {report['implemented_layers_count']}",
        f"- implementation_coverage_percent: {report['implementation_coverage_percent']}",
        f"- live_policy_status: {report['live_policy_status']}",
        f"- live_recommended_mode: {report['live_recommended_mode']}",
        "",
        "## Missing Layers",
    ]
    if report["missing_layers"]:
        for item in report["missing_layers"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Unblock Conditions"])
    for item in report["unblock_conditions"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase E stack drift report.")
    parser.add_argument("--stack", default="memory/FRONT/ECOSYSTEM_SAFETY_RESOURCE_STACK_V1.json")
    parser.add_argument("--policy", default="memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT.json")
    parser.add_argument("--output-json", default="memory/FRONT/PHASE_E_DRIFT_REPORT.json")
    parser.add_argument("--output-md", default="memory/FRONT/PHASE_E_DRIFT_REPORT.md")
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args(argv)

    root = Path(".").resolve()
    stack = load_json(Path(args.stack).resolve())
    policy = load_json(Path(args.policy).resolve())
    report = build_drift_report(root, stack, policy)

    out_json = Path(args.output_json).resolve()
    out_md = Path(args.output_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        "PHASE_E_DRIFT_OK "
        f"coverage={report['implementation_coverage_percent']} missing={len(report['missing_layers'])}"
    )
    if args.fail_on_missing and report["missing_layers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
