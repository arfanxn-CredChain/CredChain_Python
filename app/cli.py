"""Typer CLI for CredChain Python AI service.

Commands:
  generate-api-key  Create a 64-char hex API key and write it to an env file.
"""

import secrets
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def generate_api_key(
    env: str = typer.Option(
        ".env", "--env", "-e",
        help="Path to the env file to update (default: .env)",
    ),
) -> None:
    """Generate a cryptographically secure API key and write it to the env file."""
    key = secrets.token_hex(32)

    env_path = Path(env)
    if not env_path.exists():
        env_path.touch()

    lines = env_path.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith("API_KEY="):
            lines[i] = f"API_KEY={key}"
            found = True
            break

    if not found:
        lines.append(f"API_KEY={key}")

    env_path.write_text("\n".join(lines) + "\n")

    typer.echo(key)


if __name__ == "__main__":
    app()
