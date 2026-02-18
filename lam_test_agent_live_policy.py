from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _as_bool(value: Any) -> bool:
    return isinstance(value, bool) and value


def evaluate_live_activation_policy(
    telemetry: dict[str, Any],
    growth: dict[str, Any],
    *,
    dirty_repo_budget: int = 0,
    p0_budget: int = 0,
) -> dict[str, Any]:
    t_summary = telemetry.get("summary", {})
    g_summary = growth.get("summary", {})
    missing_paths = growth.get("missing_submodule_paths", [])
    routes = growth.get("routes", [])

    checks = []

    dns_ok = _as_bool(t_summary.get("github_dns_resolvable"))
    local_mirror_ok = _as_bool(t_summary.get("local_dependency_mirror_ready"))
    network_ok = dns_ok or local_mirror_ok
    checks.append(
        {
            "id": "network_resolution_gate",
            "ok": network_ok,
            "details": (
                f"github_dns_resolvable={dns_ok}, "
                f"local_dependency_mirror_ready={local_mirror_ok}"
            ),
            "severity": "critical",
        }
    )

    live_ready = _as_bool(g_summary.get("live_ready"))
    submodule_ok = live_ready and isinstance(missing_paths, list) and len(missing_paths) == 0
    checks.append(
        {
            "id": "submodule_readiness_gate",
            "ok": submodule_ok,
            "details": f"live_ready={live_ready}, missing_submodule_paths={len(missing_paths) if isinstance(missing_paths, list) else 'invalid'}",
            "severity": "critical",
        }
    )

    degraded_conformance_ok = True
    degraded_routes = 0
    if isinstance(routes, list):
        for route in routes:
            if not isinstance(route, dict):
                continue
            if route.get("expected_status") == "degraded":
                degraded_routes += 1
                if not isinstance(route.get("has_failure_assertions"), bool) or not route.get("has_failure_assertions"):
                    degraded_conformance_ok = False
                if not isinstance(route.get("has_contract_assertions"), bool) or not route.get("has_contract_assertions"):
                    degraded_conformance_ok = False
    checks.append(
        {
            "id": "degraded_mode_conformance_gate",
            "ok": degraded_conformance_ok,
            "details": f"degraded_routes={degraded_routes}, required_assertions=contract+failure",
            "severity": "critical",
        }
    )

    dirty_repos = int(t_summary.get("dirty_repos", 0)) if isinstance(t_summary.get("dirty_repos", 0), int) else 0
    dirty_ok = dirty_repos <= dirty_repo_budget
    checks.append(
        {
            "id": "dirty_repo_budget_gate",
            "ok": dirty_ok,
            "details": f"dirty_repos={dirty_repos}, budget={dirty_repo_budget}",
            "severity": "high",
        }
    )

    priority_counts = g_summary.get("priority_counts", {})
    p0_count = int(priority_counts.get("P0", 0)) if isinstance(priority_counts, dict) and isinstance(priority_counts.get("P0", 0), int) else 0
    p0_ok = p0_count <= p0_budget
    checks.append(
        {
            "id": "p0_gap_budget_gate",
            "ok": p0_ok,
            "details": f"p0_count={p0_count}, budget={p0_budget}",
            "severity": "critical",
        }
    )

    deadloop_summary = g_summary.get("deadloop_cross_repo", {})
    checkpoint_ok = (
        isinstance(deadloop_summary, dict)
        and _as_bool(deadloop_summary.get("has_cross_repo_assertions"))
        and _as_bool(deadloop_summary.get("guard_script_present"))
        and _as_bool(deadloop_summary.get("ecosystem_scan_script_present"))
        and _as_bool(deadloop_summary.get("cross_repo_ready"))
    )
    checks.append(
        {
            "id": "growth_checkpoint_gate",
            "ok": checkpoint_ok,
            "details": (
                "requires summary.deadloop_cross_repo "
                "with cross_repo_assertions+guard+scan+ready all true"
            ),
            "severity": "critical",
        }
    )

    archivator_scope_active = _as_bool(t_summary.get("archivator_scope_active"))
    archivator_handoff_ok = _as_bool(t_summary.get("archivator_handoff_ok"))
    archivator_missing = (
        int(t_summary.get("archivator_missing_mirrors_count", 0))
        if isinstance(t_summary.get("archivator_missing_mirrors_count", 0), int)
        else 0
    )
    archivator_stale = (
        int(t_summary.get("archivator_stale_mirrors_count", 0))
        if isinstance(t_summary.get("archivator_stale_mirrors_count", 0), int)
        else 0
    )
    archivator_gate_ok = (not archivator_scope_active) or archivator_handoff_ok
    checks.append(
        {
            "id": "archivator_handoff_gate",
            "ok": archivator_gate_ok,
            "details": (
                "requires Archivator mirror freshness for workflow snapshots "
                f"when scope_active=true; scope_active={archivator_scope_active}, "
                f"handoff_ok={archivator_handoff_ok}, missing={archivator_missing}, stale={archivator_stale}"
            ),
            "severity": "critical",
        }
    )

    semantic_scope_active = _as_bool(t_summary.get("semantic_identity_scope_active"))
    semantic_identity_ok = _as_bool(t_summary.get("semantic_identity_ok"))
    semantic_unresolved = (
        int(t_summary.get("semantic_identity_unresolved_count", 0))
        if isinstance(t_summary.get("semantic_identity_unresolved_count", 0), int)
        else 0
    )
    semantic_provisional = (
        int(t_summary.get("semantic_identity_provisional_count", 0))
        if isinstance(t_summary.get("semantic_identity_provisional_count", 0), int)
        else 0
    )
    semantic_templated = (
        int(t_summary.get("semantic_identity_templated_true_name_count", 0))
        if isinstance(t_summary.get("semantic_identity_templated_true_name_count", 0), int)
        else 0
    )
    semantic_gate_ok = (not semantic_scope_active) or semantic_identity_ok
    checks.append(
        {
            "id": "semantic_identity_governance_gate",
            "ok": semantic_gate_ok,
            "details": (
                "blocks rollout on unresolved/provisional/template identity naming in subtree maps; "
                f"scope_active={semantic_scope_active}, identity_ok={semantic_identity_ok}, "
                f"unresolved={semantic_unresolved}, provisional={semantic_provisional}, templated={semantic_templated}"
            ),
            "severity": "critical",
        }
    )

    critical_fail = any((not c["ok"]) and c["severity"] == "critical" for c in checks)
    status = "READY" if not critical_fail else "BLOCKED"
    recommended_mode = "live_plus_mock" if status == "READY" else "mock_only"
    blockers = [c for c in checks if not c["ok"]]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "recommended_mode": recommended_mode,
        "dirty_repo_budget": dirty_repo_budget,
        "p0_budget": p0_budget,
        "checks": checks,
        "blockers": blockers,
    }


def render_policy_markdown(policy: dict[str, Any]) -> str:
    lines = [
        "# LIVE_ACTIVATION_POLICY_REPORT",
        "",
        f"- generated_at_utc: {policy.get('generated_at_utc')}",
        f"- status: {policy.get('status')}",
        f"- recommended_mode: {policy.get('recommended_mode')}",
        f"- dirty_repo_budget: {policy.get('dirty_repo_budget')}",
        f"- p0_budget: {policy.get('p0_budget')}",
        "",
        "## Checks",
        "| Check | OK | Severity | Details |",
        "|---|---:|---|---|",
    ]
    for c in policy.get("checks", []):
        lines.append(f"| {c['id']} | {int(c['ok'])} | {c['severity']} | {c['details']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate live activation policy gates.")
    parser.add_argument("--telemetry", default="memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT.json")
    parser.add_argument("--growth", default="memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json")
    parser.add_argument("--output-json", default="memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT.json")
    parser.add_argument("--output-md", default="memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT.md")
    parser.add_argument("--dirty-repo-budget", type=int, default=0)
    parser.add_argument("--p0-budget", type=int, default=0)
    parser.add_argument("--enforce-ready", action="store_true")
    parser.add_argument("--enforce-critical", action="store_true")
    parser.add_argument("--ignore-check", action="append", default=[])
    args = parser.parse_args(argv)

    telemetry_path = Path(args.telemetry).resolve()
    growth_path = Path(args.growth).resolve()
    if not telemetry_path.exists():
        print(f"LIVE_POLICY_FAIL: telemetry not found: {telemetry_path}")
        return 2
    if not growth_path.exists():
        print(f"LIVE_POLICY_FAIL: growth snapshot not found: {growth_path}")
        return 2

    try:
        telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
        growth = json.loads(growth_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"LIVE_POLICY_FAIL invalid_json error={type(exc).__name__}")
        return 2
    if not isinstance(telemetry, dict):
        print("LIVE_POLICY_FAIL telemetry_json_must_be_object")
        return 2
    if not isinstance(growth, dict):
        print("LIVE_POLICY_FAIL growth_json_must_be_object")
        return 2
    policy = evaluate_live_activation_policy(
        telemetry,
        growth,
        dirty_repo_budget=args.dirty_repo_budget,
        p0_budget=args.p0_budget,
    )

    out_json = Path(args.output_json).resolve()
    out_md = Path(args.output_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(policy, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    out_md.write_text(render_policy_markdown(policy), encoding="utf-8")

    print(f"LIVE_POLICY_OK status={policy['status']} mode={policy['recommended_mode']}")
    if args.enforce_ready and policy["status"] != "READY":
        return 1
    if args.enforce_critical:
        ignored = set(args.ignore_check)
        critical_blockers = [
            b
            for b in policy.get("blockers", [])
            if isinstance(b, dict)
            and b.get("severity") == "critical"
            and b.get("id") not in ignored
        ]
        if critical_blockers:
            for blocker in critical_blockers:
                print(
                    "LIVE_POLICY_FAIL critical_blocker "
                    f"id={blocker.get('id')} details={blocker.get('details')}"
                )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
