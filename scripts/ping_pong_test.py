from pathlib import Path

from lam_test_agent_bootstrap import (
    extend_agent_sys_path,
    missing_agent_src_paths,
    missing_paths_as_text,
)


ROOT = Path(__file__).resolve().parents[1]
extend_agent_sys_path(ROOT)


def main() -> None:
    missing = missing_agent_src_paths(ROOT)
    if missing:
        raise SystemExit(
            "Missing submodule agent sources. Run scripts/bootstrap_submodules.sh first: "
            + missing_paths_as_text(missing)
        )

    from codex_agent.core import Core  # type: ignore
    from agents.com_agent import ComAgent  # type: ignore

    codex = Core()
    comm = ComAgent()
    comm.register_agent("codex", codex)

    comm.send_data("codex", {"msg": "ping"})
    _, payload = comm.receive_data()
    reply = codex.answer(payload["msg"])
    print("→", reply)


if __name__ == "__main__":
    main()
