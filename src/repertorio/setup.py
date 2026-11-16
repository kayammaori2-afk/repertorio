"""Generate connection snippets without modifying host settings or learner data."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def setup(output: Path, db: Path, profile: str) -> dict[str, Any]:
    from .cli import write_private
    from .server import validate_profile

    validate_profile(profile)
    output = Path(os.path.abspath(output))
    # A new directory is a simple, reviewable no-overwrite boundary.
    output.mkdir(parents=True, exist_ok=False)
    args = ["-m", "repertorio", "--db", str(db.resolve()), "--profile", profile, "serve"]
    server = {"command": sys.executable, "args": args}
    artifacts = {
        "claude.mcp.json": json.dumps({"mcpServers": {"repertorio": server}}, indent=2),
        "vscode.mcp.json": json.dumps({"servers": {"repertorio": {"type": "stdio", **server}}}, indent=2),
        "codex.config.toml": "[mcp_servers.repertorio]\ncommand = "
        + json.dumps(sys.executable, ensure_ascii=False).replace("\x7f", "\\u007f")
        + "\nargs = "
        + json.dumps(args, ensure_ascii=False).replace("\x7f", "\\u007f")
        + "\n",
        "START-HERE.txt": (
            "Repertorio — primeiro uso / first use\n\n"
            "1. Use o arquivo do seu assistente como trecho de configuração. Se já existe uma configuração, mescle apenas a entrada repertorio. Não substitua o arquivo inteiro.\n"
            "2. Reconecte o MCP no assistente e permita a conexão local.\n"
            "3. Diga: Quero estudar com Repertorio. Mostre os assuntos disponíveis e me ajude a começar sem presumir o que conheço.\n"
            "4. O assistente chama learning_options; você pode pular o cadastro e estudar diretamente.\n"
            "5. Para retomar: Leia meu perfil do Repertorio e continue. Para corrigir: Corrija apenas o que eu indicar.\n\n"
            "These are snippets, not an automatic installation. Merge only the repertorio entry into existing host settings; reconnect the MCP server. Ask the assistant to call learning_options.\n"
            "No profile has been created, no host settings changed, and delete permission is not enabled. A connected assistant/provider can receive the data you share.\n"
            "If tools do not appear, check the exact interpreter/database paths, run doctor with this database, and reopen the host. Support differs by assistant.\n"
        ),
    }
    for name, content in artifacts.items():
        write_private(output / name, content + "\n")
    return {
        "directory": str(output),
        "files": list(artifacts),
        "host_settings_changed": False,
        "database_created": False,
        "delete_granted": False,
        "next_step": "Read START-HERE.txt and merge the snippet for your assistant.",
    }
