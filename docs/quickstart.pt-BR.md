# Primeiro uso

O Repertorio guarda repertório e evidências para o assistente que você já usa. O servidor funciona localmente, sem chave própria de IA. O assistente continua responsável pela conversa.

## Instalar e experimentar

Instale [Python 3.13](https://www.python.org/downloads/) e [uv](https://docs.astral.sh/uv/getting-started/installation/). No terminal:

```sh
git clone https://github.com/kayammaori2-afk/repertorio.git
cd repertorio
uv sync --locked
uv run repertorio doctor
uv run repertorio demo
```

A demo usa uma base sintética temporária. Ela grava, reinicia o servidor, recupera o perfil e comprova que uma correção muda a seleção. Pode repetir o comando. Para guardar banco e transcrição, escolha arquivos novos:

```sh
uv run repertorio --db demo.sqlite3 --profile demo demo --output demo-transcript.json
```

Também é possível baixar o wheel na [release v0.2.0](https://github.com/kayammaori2-afk/repertorio/releases/tag/v0.2.0), instalar com `python -m pip install CAMINHO_DO_WHEEL` e executar `repertorio demo`. Para desenvolver e rodar todos os testes, prefira o repositório com uv.

## Conectar ao assistente

Gere os caminhos automaticamente:

```sh
uv run repertorio --profile student setup --output host-setup
```

Leia `host-setup/START-HERE.txt` e mescle somente a entrada `repertorio` no assistente escolhido. O comando gera os arquivos; não altera sua configuração existente nem cadastra repertório. Se falhar por acesso/permissão, preserve a pasta parcial, resolva o acesso e tente outra pasta nova em `--output`. O arquivo START-HERE inclui o diagnóstico com o interpretador, banco e perfil escolhidos. Reconecte o MCP e diga: “Quero estudar com Repertorio. Mostre os assuntos e me ajude a começar sem presumir o que conheço.” Você pode pular a personalização. Para usar outro banco, coloque `--db CAMINHO_PRIVADO` antes de `setup`. As instruções manuais abaixo continuam válidas.

Execute `uv run python -c "import sys; print(sys.executable)"`. Use o caminho absoluto mostrado como comando MCP. Os argumentos são `-m repertorio --db CAMINHO_ABSOLUTO_DO_BANCO --profile student serve`. Escolha um local privado para o banco e use o mesmo caminho e perfil nos assistentes que devem compartilhar os dados.

- Claude Code: adapte [examples/claude.mcp.json](../examples/claude.mcp.json).
- Codex: adapte [examples/codex.config.toml](../examples/codex.config.toml).
- VS Code/Copilot: adapte [examples/vscode.mcp.json](../examples/vscode.mcp.json); esse host ainda não teve seu fluxo executado.

No Windows o Python costuma estar em `.venv/Scripts/python.exe`; no Linux/macOS, `.venv/bin/python`. Substitua os marcadores nos exemplos. Preserve as aprovações de ferramentas do assistente e copie a [instrução de sessão](tutor-instructions.pt-BR.md).

Peça: “Já faço compras semanais com orçamento e comparo preços e alternativas; cadastre essa experiência que já pratiquei. Use `everyday:shopping`, confirme minha familiaridade e me explique `opportunity_cost`, mostrando onde a analogia deixa de funcionar.” O catálogo inicial exige IDs e elementos explícitos. Cadastrar uma obra qualquer não cria automaticamente uma boa analogia. Quando faltar referência adequada, o assistente recebe orientação para explicar diretamente.

## Corrigir, fazer backup e restaurar

Uma correção usa a revisão atual do registro. Em caso de conflito, consulte o perfil novamente. Preserve o identificador da operação ao repetir uma escrita que falhou; use IDs aleatórios sem informações pessoais. O assistente só deve confirmar que salvou após o sucesso da ferramenta.

```sh
uv run repertorio --profile student export --output PRIVATE_DIR/profile.json
uv run repertorio --profile restored import --input PRIVATE_DIR/profile.json
uv run repertorio --profile restored import --input PRIVATE_DIR/profile.json --apply
```

Use uma pasta privada fora do repositório para `PRIVATE_DIR`. A importação mostra uma prévia antes de aplicar. Guarde o arquivo em local privado. `export --format summary --output PRIVATE_DIR/context.txt` gera um resumo para uso manual em outro assistente, válido para aquele momento. [CSV, exclusão e limites de retenção](data.md).

## Verificar e contribuir

Para preparar um piloto vazio, com roteiro, consentimento em rascunho e formulários separados dos gabaritos:

```sh
uv run repertorio study init --output PRIVATE_DIR/pilot
uv run repertorio study check --directory PRIVATE_DIR/pilot
```

O segundo comando retorna código 3 enquanto faltarem informações e revisões humanas. Isso é esperado: materiais preparados não significam recrutamento autorizado. Leia `LEIA-PRIMEIRO.md` no kit. [Nova avaliação de tutores](tutor-evaluation.md) · [Escopo da versão 0.2](v0.2.0.md).

```sh
uv run python scripts/verify.py
uv run repertorio evaluate --output evidence/evaluation
uv run repertorio pilot --output evidence/pilot
```

O último comando analisa dados artificiais, não resultados de alunos. Consulte [os resultados e limites](verification.md). O [README](../README.md) explica HTTP autenticado, arquitetura e contribuição. A [matriz de compatibilidade](compatibility.md) distingue testes reais de configurações ainda não executadas. Código, documentação e exemplos originais usam [MIT](../LICENSE).
