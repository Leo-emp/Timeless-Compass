# Tests for the tc command-line entry point.
import pytest

from tc.cli import main


def test_help_lists_commands(capsys):
    # --help makes argparse print usage and exit; we catch the exit and read what it printed
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for name in ("doctor", "new", "status", "learn"):
        assert name in out
