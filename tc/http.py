# All web requests go through curl (Python's own HTTP client hung on this machine; curl never did).
# Headers (which may contain API keys) are written to a temporary file and passed as -H @file,
# so keys never appear on the command line or in any log.
import json
import os
import subprocess
import tempfile


class HttpError(Exception):
    def __init__(self, status: int, snippet: str):
        super().__init__(f"HTTP {status}: {snippet[:200]}")
        self.status, self.snippet = status, snippet


def _curl(url: str, headers: dict[str, str] | None, body: bytes | None, timeout: int, runner) -> tuple[int, bytes, str]:
    """Run one curl request. Returns (status code, response body bytes, content type)."""
    fd_out, out_path = tempfile.mkstemp(suffix=".body"); os.close(fd_out)
    fd_h, hdr_path = tempfile.mkstemp(suffix=".hdr"); os.close(fd_h)
    in_path = None
    try:
        with open(hdr_path, "w", encoding="utf-8") as f:
            for k, v in (headers or {}).items():
                f.write(f"{k}: {v}\n")
        cmd = ["curl", "-s", "-o", out_path, "-w", "%{http_code} %{content_type}", "--max-time", str(timeout), "-H", f"@{hdr_path}"]
        if body is not None:
            fd_i, in_path = tempfile.mkstemp(suffix=".in"); os.close(fd_i)
            with open(in_path, "wb") as f:
                f.write(body)
            cmd += ["--data-binary", f"@{in_path}"]
        cmd.append(url)
        res = runner(cmd, capture_output=True, timeout=timeout + 15)
        meta = (res.stdout.decode("utf-8", "replace") if isinstance(res.stdout, bytes) else res.stdout).strip()
        status_s, _, ctype = meta.partition(" ")
        status = int(status_s) if status_s.isdigit() else 0          # 0 = no connection / timeout
        if res.returncode != 0:                                     # curl died (e.g. 28 timeout, 18/56 cut-off):
            status = 0                                              # never trust a partial body
        with open(out_path, "rb") as f:
            data = f.read()
        return status, data, ctype.strip()
    finally:
        for p in (out_path, hdr_path, in_path):
            if p and os.path.exists(p):
                os.remove(p)


def get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 60, runner=subprocess.run):
    status, data, _ = _curl(url, headers, None, timeout, runner)
    if not 200 <= status < 300:
        raise HttpError(status, data.decode("utf-8", "replace"))
    return json.loads(data.decode("utf-8"))


def post_bytes(url: str, body: bytes, headers: dict[str, str], timeout: int = 180, runner=subprocess.run) -> tuple[int, bytes, str]:
    """POST raw bytes; returns (status, body, content type) without raising, the caller decides."""
    return _curl(url, headers, body, timeout, runner)
