from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(ROOT / "LAM_Test" / "agents" / "codex-agent" / "src"),
    str(ROOT / "LAM_Test" / "agents" / "comm-agent" / "src"),
])

from codex_agent.core import Core           # type: ignore
from interfaces.com_agent_interface import ComAgent  # type: ignore


def test_ping_pong() -> None:
    codex = Core()
    comm = ComAgent()
    comm.register_agent("codex", codex)

    comm.send_data("codex", {"msg": "ping"})
    _, payload = comm.receive_data()
    reply = codex.answer(payload["msg"])

    assert (isinstance(reply, dict) and reply.get("reply") == "pong") or reply == "pong"
