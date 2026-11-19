# Tests for `tc doctor` and the curl-based HTTP helper.
import subprocess

import pytest

from tc import doctor, http
from tc.config import Config


class FakeCurl:
    """Stands in for subprocess.run when tc.http calls curl: returns a chosen status + body."""
    def __init__(self, status: int, body: bytes = b"{}", ctype: str = "application/json"):
        self.status, self.body, self.ctype = status, body, ctype

    def __call__(self, cmd, **kw):
        out_path = cmd[cmd.index("-o") + 1]
        with open(out_path, "wb") as f:
            f.write(self.body)
        return subprocess.CompletedProcess(cmd, 0, stdout=f"{self.status} {self.ctype}".encode(), stderr=b"")


def test_http_error_raises():
    with pytest.raises(http.HttpError) as e:
        http.get_json("https://example.test/x", runner=FakeCurl(404, b'{"error": "nope"}'))
    assert e.value.status == 404


def _env(**over):
    base = dict(cfg=Config(azure_key="k", azure_region="eastus"), which=lambda name: f"/bin/{name}",
                disk_free_gb=lambda: 50.0, can_import=lambda mod: True, exists=lambda p: True,
                azure_ok=lambda cfg: True)
    base.update(over)
    return base


def test_all_good_returns_zero():
    checks = doctor.run_checks(**_env())
    assert doctor.exit_code(checks) == 0


def test_missing_azure_key_fails_required():
    checks = doctor.run_checks(**_env(cfg=Config()))
    bad = [c for c in checks if not c.ok and c.required]
    assert any("Azure" in c.name for c in bad)
    assert doctor.exit_code(checks) == 1


def test_low_disk_warns_not_fails():
    checks = doctor.run_checks(**_env(disk_free_gb=lambda: 8.0))
    disk = next(c for c in checks if "disk" in c.name.lower())
    assert disk.ok is False and disk.required is False
    assert doctor.exit_code(checks) == 0
