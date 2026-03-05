import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_SH = REPO_ROOT / "devkit" / "patch.sh"


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


class TestPhaseBPatchRuntimeContract(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.repo = Path(self.td.name)
        run(["git", "init"], self.repo)
        run(["git", "config", "user.email", "phaseb@example.com"], self.repo)
        run(["git", "config", "user.name", "phaseb"], self.repo)
        (self.repo / "f.txt").write_text("one\n", encoding="utf-8")
        (self.repo / "task_spec.yaml").write_text("task_id: t\n", encoding="utf-8")
        run(["git", "add", "f.txt", "task_spec.yaml"], self.repo)
        run(["git", "commit", "-m", "init"], self.repo)

    def tearDown(self) -> None:
        self.td.cleanup()

    def _patch(self, new="two"):
        target = self.repo / "f.txt"
        p = self.repo / "c.patch"
        target.write_text(f"{new}\n", encoding="utf-8")
        diff = run(["git", "diff", "--", "f.txt"], self.repo)
        p.write_text(diff.stdout, encoding="utf-8")
        run(["git", "checkout", "--", "f.txt"], self.repo)
        return p

    def test_success(self) -> None:
        p = self._patch("two")
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        r = run(["bash", str(PATCH_SH), "--file", str(p), "--sha256", sha, "--task-id", "ok", "--spec-file", "task_spec.yaml"], self.repo)
        self.assertEqual(r.returncode, 0)
        self.assertIn("status=success", r.stdout)
        self.assertIn("error_code=NONE", r.stdout)
        self.assertIn("trace: task_id=ok", r.stdout)

    def test_missing_spec_file(self) -> None:
        p = self._patch("two")
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        r = run(["bash", str(PATCH_SH), "--file", str(p), "--sha256", sha, "--task-id", "x"], self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("error_code=PATCH_SPEC_FILE_REQUIRED", r.stdout)

    def test_integrity_mismatch(self) -> None:
        p = self._patch("two")
        r = run(["bash", str(PATCH_SH), "--file", str(p), "--sha256", "0" * 64, "--task-id", "x", "--spec-file", "task_spec.yaml"], self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("status=integrity_mismatch", r.stdout)
        self.assertIn("error_code=PATCH_SHA256_MISMATCH", r.stdout)

    def test_conflict_detected(self) -> None:
        p = self._patch("two")
        corrupted = p.read_text(encoding="utf-8").replace("-one", "-zzz", 1)
        p.write_text(corrupted, encoding="utf-8")

        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        r = run(["bash", str(PATCH_SH), "--file", str(p), "--sha256", sha, "--task-id", "x", "--spec-file", "task_spec.yaml"], self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("status=conflict_detected", r.stdout)
        self.assertIn("error_code=PATCH_CONFLICT_DETECTED", r.stdout)


if __name__ == "__main__":
    unittest.main()
