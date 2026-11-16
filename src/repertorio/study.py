"""Unpopulated pilot kit and fail-closed readiness checks. No recruitment or telemetry."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
from importlib.resources import files
from pathlib import Path
from typing import Any

from .experiment import digest, read_json, write_json
from .pilot import synthetic_rows

REQUIRED = (
    "responsible_contact",
    "withdrawal_contact",
    "study_dates",
    "provider",
    "model_version",
    "screening_rule",
    "privacy_and_retention_plan",
    "ethics_review_or_applicability_reference",
    "pedagogical_review_reference",
    "scorer_training_reference",
)
TASKS = ("connect", "first_lesson", "resume", "correct", "skip_personalization")
CONSENT_FIELDS = (
    "responsible_contact",
    "withdrawal_contact",
    "study_dates",
    "provider",
    "model_version",
    "privacy_and_retention_plan",
    "activities_and_duration",
    "costs_and_compensation",
    "provider_data_handling",
    "withdrawal_and_limits",
)
USABILITY_FIELDS = (
    "dataset_kind",
    "participant_id",
    "task",
    "completed",
    "assisted",
    "seconds",
    "failure_code",
    "returned_within_7_days",
)


def csv_template(fields: list[str] | tuple[str, ...]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(fields)
    return stream.getvalue()


def initialize(output: Path) -> dict[str, Any]:
    from .cli import write_private

    output.mkdir(parents=True, exist_ok=False)
    protocol = {
        "version": "pilot-kit-v0.2",
        "status": "DRAFT_NOT_RECRUITING",
        "language": "pt-BR",
        "phase_1": "Six adult usability sessions; operational starting target, not statistical power",
        "phase_2": "Existing 36-adult A/B/C feasibility protocol; learning estimates exploratory",
        "primary_usability_measure": "unassisted first_lesson completion among all enrolled usability participants",
        "progression_rule": "Review every failure. Before a learning pilot: zero unresolved critical privacy/data-loss defects; at least 5/6 complete first_lesson unassisted and 5/6 resume/correct. These are author-chosen operational thresholds, not validated cutoffs.",
        "generation_settings": {"max_output_tokens": 800, "temperature": 0},
        "consent_text_reviewed": False,
        "data_access_and_deletion_tested": False,
        "recruitment_authorized": False,
        **dict.fromkeys(REQUIRED),
        **dict.fromkeys(CONSENT_FIELDS),
    }
    write_json(output / "study.json", protocol)
    bank = json.loads(files("repertorio").joinpath("data/pilot_items.json").read_text(encoding="utf-8"))
    for form in ("baseline", "X", "Y"):
        questions = [item for item in bank["items"] if item["form"] == form]
        text = "Avaliação individual — " + form + "\n\nCódigo: __________\n\n"
        text += "Responda sem IA, consulta ou ajuda. Você pode deixar uma resposta em branco. Não escreva seu nome.\n\n"
        text += "\n\n".join(
            item["prompt"] + "\n\nResposta: ______________________________" for item in questions
        )
        write_private(output / "participant" / f"form-{form}.txt", text + "\n")
    write_json(output / "operator" / "item-bank-with-answers.json", bank)
    protocol_resource = files("repertorio").joinpath("data/pilot-protocol.md")
    protocol_text = (
        protocol_resource.read_text(encoding="utf-8")
        if protocol_resource.is_file()
        else (Path(__file__).resolve().parents[2] / "docs/pilot.md").read_text(encoding="utf-8")
    )
    write_private(output / "operator" / "learning-protocol.md", protocol_text)
    write_private(output / "usability.csv", csv_template(USABILITY_FIELDS))
    write_private(output / "learning.csv", csv_template(list(synthetic_rows()[0])))
    write_private(
        output / "scoring.csv",
        csv_template(
            [
                "participant_id",
                "form",
                "timepoint",
                "item_id",
                "scorer_id",
                "criterion_1",
                "criterion_2",
                "criterion_3",
                "criterion_4",
                "error_codes",
                "adjudication_reason",
            ]
        ),
    )
    write_private(
        output / "flow.csv",
        csv_template(
            [
                "pseudonymous_screening_id",
                "eligible",
                "consented",
                "enrolled",
                "randomized",
                "withdrawn",
                "followup_completed",
                "non_sensitive_reason",
            ]
        ),
    )
    guide = files("repertorio").joinpath("data/study-guide.pt-BR.md").read_text(encoding="utf-8")
    write_private(output / "LEIA-PRIMEIRO.md", guide)
    write_private(
        output / "participant" / "consent-DRAFT.txt",
        (
            "RASCUNHO — completar e revisar antes de apresentar a participantes\n\n"
            "Você está sendo convidado(a) a testar uma ferramenta que fornece contexto à IA que você usa. Sua participação é voluntária. Pode pular perguntas ou encerrar sem justificar. Não há benefício educacional garantido.\n"
            "Fase, duração, equipe e contato: [preencher]. Atividades e eventual sorteio de condição: [preencher conforme a fase].\n"
            "Serão registrados código aleatório, conclusão das tarefas, tempo, ajuda recebida e, na fase de aprendizagem, respostas e pontuação. Não inclua dados sensíveis nem nomes de terceiros no repertório. Não gravaremos a tela ou a conversa inteira por padrão.\n"
            "O assistente e seu provedor podem receber os dados que você compartilhar. Provedor, modelo, política aplicável e riscos residuais: [preencher]. O banco local, as respostas e o histórico do assistente têm ciclos de exclusão separados.\n"
            "Acesso, local de armazenamento, prazo de retenção, retirada e limites após agregação: [preencher]. Contato para dúvidas e retirada: [preencher]. Custos ou compensação: [preencher].\n"
            "Declaração: tenho 18 anos ou mais, compreendi a atividade e escolho participar. Forma de registrar o consentimento: [definir com responsável].\n"
        ),
    )
    return {
        "directory": str(output),
        "status": "materials_prepared",
        "human_rows": 0,
        "recruitment_ready": False,
        "next": "Complete study.json and consent; run study check. Human reviews remain required.",
    }


def consent_text(protocol: dict[str, Any]) -> str:
    for field in CONSENT_FIELDS:
        value = protocol.get(field)
        if (
            not isinstance(value, str)
            or not value.strip()
            or value.strip().lower() in {"pending", "todo", "unknown", "latest"}
        ):
            raise ValueError(f"Complete consent field: {field}")
    return (
        "Informações para participação voluntária — Repertorio\n\n"
        "Objetivo: testar a experiência de uma ferramenta que fornece contexto à IA. Não há benefício educacional garantido. Participação apenas de adultos com 18 anos ou mais que possam consentir.\n\n"
        f"Equipe e dúvidas: {protocol['responsible_contact']}\nDatas: {protocol['study_dates']}\n"
        f"Atividades, fase, sorteio quando aplicável e duração: {protocol['activities_and_duration']}\n"
        f"Custos e compensação: {protocol['costs_and_compensation']}\n\n"
        "Você pode pular perguntas e interromper sem justificar. Não compartilhe dados sensíveis nem nomes de terceiros. Sem gravação de tela ou histórico completo por padrão. Registraremos código aleatório, conclusão, tempo e ajuda; na fase de aprendizagem, respostas e pontuações.\n\n"
        f"Assistente/provedor: {protocol['provider']}; modelo: {protocol['model_version']}.\n"
        f"Dados enviados ao provedor e política aplicável: {protocol['provider_data_handling']}\n"
        f"Armazenamento, acesso e retenção: {protocol['privacy_and_retention_plan']}\n"
        f"Retirada e limites para cópias/agregados: {protocol['withdrawal_and_limits']}\n"
        f"Contato de retirada: {protocol['withdrawal_contact']}\n\n"
        "Consentimento deve ser obtido separadamente após esclarecimento de dúvidas. Este documento não registra consentimento nem comprova aprovação ética.\n"
    )


def render_consent(directory: Path) -> dict[str, Any]:
    from .cli import write_private

    if (directory / "study-freeze.json").exists():
        raise ValueError("Study is frozen; revise materials in a new study version.")
    text = consent_text(read_json(directory / "study.json"))
    write_private(directory / "participant/consent-DRAFT.txt", text, replace=True)
    return {"consent_rendered": True, "human_review_required": True, "consent_obtained": False}


def check(directory: Path) -> dict[str, Any]:
    protocol = read_json(directory / "study.json")
    missing = [
        field
        for field in REQUIRED
        if not isinstance(protocol.get(field), str)
        or not protocol[field].strip()
        or protocol[field].strip().lower() in {"pending", "todo", "unknown", "latest"}
    ]
    missing.extend(
        field
        for field in ("consent_text_reviewed", "data_access_and_deletion_tested", "recruitment_authorized")
        if protocol.get(field) is not True
    )
    consent = (directory / "participant" / "consent-DRAFT.txt").read_text(encoding="utf-8")
    if not consent.strip() or "[" in consent or "RASCUNHO" in consent:
        missing.append("complete_and_review_participant_consent")
    try:
        if consent != consent_text(protocol):
            missing.append("render_consent_from_current_fields")
    except ValueError:
        missing.append("complete_required_consent_fields")
    settings = protocol.get("generation_settings", {})
    if type(settings.get("max_output_tokens")) is not int or not 1 <= settings["max_output_tokens"] <= 4096:
        missing.append("generation_settings")
    return {
        "materials_prepared": True,
        "ready_by_operator_declarations": not missing,
        "pending": missing,
        "human_reviews_verified_by_software": False,
        "interpretation": "Checks completeness, not legal/ethical approval, pedagogical validity or consent authenticity.",
    }


def freeze(directory: Path) -> dict[str, Any]:
    readiness = check(directory)
    if readiness["pending"]:
        raise ValueError(
            "Pilot has pending fields/reviews. Run study check; no recruitment readiness is claimed."
        )
    names = [
        "study.json",
        "LEIA-PRIMEIRO.md",
        "participant/consent-DRAFT.txt",
        "participant/form-baseline.txt",
        "participant/form-X.txt",
        "participant/form-Y.txt",
        "operator/item-bank-with-answers.json",
        "operator/learning-protocol.md",
    ]
    manifest = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}
    write_json(directory / "study-freeze.json", manifest)
    return {"status": "locally_frozen", "hashes": manifest, "independent_registration": False}


def analyze_usability(directory: Path) -> dict[str, Any]:
    path = directory / "usability.csv"
    if path.stat().st_size > 1_048_576:
        raise ValueError("Usability CSV exceeds one MiB.")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(USABILITY_FIELDS):
            raise ValueError(
                "Unexpected usability columns; use the generated template, without names or contacts."
            )
        rows = list(reader)
    if not rows:
        raise ValueError("No observations. An empty template is not a completed pilot.")
    kinds = {row["dataset_kind"] for row in rows}
    if len(kinds) != 1 or not kinds <= {"synthetic", "human"}:
        raise ValueError("Uniform synthetic/human provenance is required.")
    if kinds == {"human"}:
        if check(directory)["pending"]:
            raise ValueError("Human analysis requires completed readiness declarations.")
        manifest = read_json(directory / "study-freeze.json")
        names = {
            "study.json",
            "LEIA-PRIMEIRO.md",
            "participant/consent-DRAFT.txt",
            "participant/form-baseline.txt",
            "participant/form-X.txt",
            "participant/form-Y.txt",
            "operator/item-bank-with-answers.json",
            "operator/learning-protocol.md",
        }
        if set(manifest) != names or any(
            hashlib.sha256((directory / name).read_bytes()).hexdigest() != manifest[name] for name in names
        ):
            raise ValueError("Study materials changed after freeze; record a new version/cohort.")
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        import re

        if not re.fullmatch(r"p-[0-9a-f]{16}", row["participant_id"]):
            raise ValueError("Use an opaque p- plus 16 random hexadecimal digits participant ID; no names.")
        key = (row["participant_id"], row["task"])
        if key in observed or row["task"] not in TASKS:
            raise ValueError("Duplicate or unknown participant task.")
        if any(
            row[field] not in {"True", "False", ""}
            for field in ("completed", "assisted", "returned_within_7_days")
        ):
            raise ValueError("Use True, False or empty for unobserved Boolean fields.")
        if row["completed"] != "True" and not row["failure_code"]:
            raise ValueError("Incomplete/unobserved tasks require a non-sensitive reason code.")
        if row["completed"] == "True" and row["assisted"] == "":
            raise ValueError("Completed tasks must record whether assistance was needed.")
        seconds = float(row["seconds"]) if row["seconds"] else None
        if seconds is not None and (not math.isfinite(seconds) or not 0 <= seconds <= 86400):
            raise ValueError("Task time must be finite nonnegative seconds, or missing.")
        observed[key] = {**row, "seconds": seconds}
    participants = {key[0] for key in observed}
    if any((participant, task) not in observed for participant in participants for task in TASKS):
        raise ValueError(
            "Record all five tasks for every enrolled participant, including not-attempted/missing tasks."
        )
    return_values = {}
    for participant in participants:
        values = {observed[(participant, task)]["returned_within_7_days"] for task in TASKS}
        if len(values) != 1:
            raise ValueError("Seven-day return must agree across a participant's task rows.")
        return_values[participant] = next(iter(values))
    measures = {}
    for task in TASKS:
        task_rows = [row for (_, name), row in observed.items() if name == task]
        times = [row["seconds"] for row in task_rows if row["seconds"] is not None]
        measures[task] = {
            "enrolled": len(participants),
            "completed": sum(row["completed"] == "True" for row in task_rows),
            "completed_unassisted": sum(
                row["completed"] == "True" and row["assisted"] == "False" for row in task_rows
            ),
            "outcome_unobserved": sum(row["completed"] == "" for row in task_rows),
            "time_observed": len(times),
            "median_seconds_observed": statistics.median(times) if times else None,
        }
    return {
        "dataset_kind": next(iter(kinds)),
        "participants": len(participants),
        "tasks": measures,
        "returned_within_7_days": sum(value == "True" for value in return_values.values()),
        "return_unobserved": sum(value == "" for value in return_values.values()),
        "input_hash": digest(rows),
        "interpretation": "Descriptive usability observations by declared provenance. No learning benefit or automatic progression approval.",
    }
