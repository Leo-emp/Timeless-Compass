# Where everything lives. Other modules read these AT CALL TIME (tc.paths.JOBS),
# so tests can point them at a temporary folder with monkeypatch.
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the timeless-compass repo folder
JOBS = ROOT / "jobs"                            # one folder per video (git-ignored)
TASTE = ROOT / "taste"                          # owner rules + learning memory
LIBRARY = ROOT / "library"                      # asset manifests (big files live in R2)
ENV_FILE = ROOT / ".env"                        # secret keys (git-ignored, never printed)
