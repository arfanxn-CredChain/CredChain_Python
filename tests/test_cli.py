"""Tests for app/cli.py — API key generation CLI."""

from unittest.mock import patch

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


class TestGenerateApiKey:
    def test_generates_64_char_hex_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FASTAPI_PORT=8081\n")

        result = runner.invoke(app, ["--env", str(env_file)])

        assert result.exit_code == 0
        key = result.stdout.strip()
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_appends_key_to_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FASTAPI_PORT=8081\n")

        result = runner.invoke(app, ["--env", str(env_file)])

        assert result.exit_code == 0
        content = env_file.read_text()
        assert "API_KEY=" in content
        key = result.stdout.strip()
        assert key in content

    def test_replaces_existing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=old-key-12345\nFASTAPI_PORT=8081\n")

        result = runner.invoke(app, ["--env", str(env_file)])

        assert result.exit_code == 0
        content = env_file.read_text()
        assert "old-key-12345" not in content
        new_key = result.stdout.strip()
        assert f"API_KEY={new_key}" in content
        assert "FASTAPI_PORT=8081" in content

    def test_default_env_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "-e" in result.stdout
        assert "--env" in result.stdout

    def test_short_flag(self):
        result = runner.invoke(app, ["-e", "/tmp/test.env"])
        assert result.exit_code == 0

    def test_key_deterministic(self, tmp_path):
        """Two invocations should produce different keys."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        with patch("app.cli.secrets.token_hex") as mock_token:
            mock_token.side_effect = ["a" * 64, "b" * 64]
            r1 = runner.invoke(app, ["--env", str(env_file)])
            r2 = runner.invoke(app, ["--env", str(env_file)])

        assert r1.stdout.strip() != r2.stdout.strip()

    def test_creates_file_if_missing(self, tmp_path):
        env_file = tmp_path / "nonexistent.env"

        result = runner.invoke(app, ["--env", str(env_file)])

        assert result.exit_code == 0
        assert env_file.exists()
        key = result.stdout.strip()
        assert f"API_KEY={key}" in env_file.read_text()
