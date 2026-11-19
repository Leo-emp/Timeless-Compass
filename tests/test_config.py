# Tests for settings + .env loading.
from tc.config import get_config, load_env


def test_load_env_strips_quotes_and_cr(tmp_path):
    f = tmp_path / ".env"
    f.write_bytes(b'A="x"\r\n#comment\nB=y\n')
    assert load_env(f) == {"A": "x", "B": "y"}


def test_config_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("TC_VOICE", raising=False)
    cfg = get_config(env_file=tmp_path / "missing.env")
    assert cfg.voice == "en-US-LewisMultilingualNeural"
    assert cfg.long_words == (1500, 1800)
    assert cfg.azure_key is None


def test_tc_voice_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TC_VOICE", "en-US-Jimmie:DragonHDFlashLatestNeural")
    cfg = get_config(env_file=tmp_path / "missing.env")
    assert cfg.voice == "en-US-Jimmie:DragonHDFlashLatestNeural"
