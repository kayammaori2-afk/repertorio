"""Regression cases from the independent v0.2 Claude review; all data artificial."""

import csv
import hashlib
import json
import subprocess

import pytest

from repertorio import experiment, pilot, study
from repertorio.cli import main


def declared_ready(directory):
    protocol = experiment.read_json(directory / "study.json")
    protocol.update(dict.fromkeys((*study.REQUIRED, *study.CONSENT_FIELDS), "Artificial declaration only"))
    protocol.update(data_access_and_deletion_tested=True, recruitment_authorized=True)
    experiment.write_json(directory / "study.json", protocol, replace=True)
    rendered = study.render_consent(directory)
    protocol.update(consent_text_reviewed=True, consent_text_reviewed_sha256=rendered["consent_sha256"])
    experiment.write_json(directory / "study.json", protocol, replace=True)
    return protocol


def learning_csv(directory, kind="synthetic", encoding="utf-8-sig"):
    rows = pilot.synthetic_rows()
    for index, row in enumerate(rows):
        row.update(participant_id=f"p-{index:016x}", dataset_kind=kind)
    with (directory / "learning.csv").open("w", encoding=encoding, newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def test_consent_review_is_bound_to_current_text_and_unchanged_render_preserves_it(tmp_path):
    study.initialize(tmp_path / "study")
    directory = tmp_path / "study"
    protocol = declared_ready(directory)
    assert study.check(directory)["ready_by_operator_declarations"]
    study.render_consent(directory)
    assert study.check(directory)["ready_by_operator_declarations"]
    protocol["withdrawal_and_limits"] = "Changed artificial withdrawal terms"
    experiment.write_json(directory / "study.json", protocol, replace=True)
    assert "consent_review_for_current_text" in study.check(directory)["pending"]
    study.render_consent(directory)
    changed = experiment.read_json(directory / "study.json")
    assert changed["consent_text_reviewed"] is False
    assert changed["consent_text_reviewed_sha256"] is None
    with pytest.raises(ValueError, match="pending"):
        study.freeze(directory)


def test_learning_wrapper_accepts_bom_preserves_frozen_numerics_and_refuses_overwrite(tmp_path, capsys):
    directory = tmp_path / "study"
    study.initialize(directory)
    rows = learning_csv(directory)
    output = tmp_path / "analysis"
    assert main(["study", "analyze-learning", "--directory", str(directory), "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["estimates"] == pilot.analyze(rows)["estimates"]
    assert result["input_sha256"] == hashlib.sha256((directory / "learning.csv").read_bytes()).hexdigest()
    original = (output / "analysis.json").read_bytes()
    with pytest.raises(FileExistsError):
        study.analyze_learning(directory, output)
    assert (output / "analysis.json").read_bytes() == original
    assert "Synthetic" in (output / "REPORT.md").read_text()


def test_learning_declared_human_requires_readiness_freeze_and_unchanged_materials(tmp_path):
    directory = tmp_path / "study"
    study.initialize(directory)
    learning_csv(directory, "human")  # Only an artificial fixture exercises this branch.
    with pytest.raises(ValueError, match="readiness"):
        study.analyze_learning(directory, tmp_path / "blocked")
    declared_ready(directory)
    with pytest.raises(ValueError, match="not frozen"):
        study.analyze_learning(directory, tmp_path / "unfrozen")
    with pytest.raises(ValueError, match="before recording"):
        study.freeze(directory)
    # Discard only this artificial fixture, freeze empty forms, then simulate collection.
    (directory / "learning.csv").write_bytes(
        study.csv_template(list(pilot.synthetic_rows()[0])).encode("utf-8")
    )
    study.freeze(directory)
    learning_csv(directory, "human")
    result = study.analyze_learning(directory, tmp_path / "accepted-fixture")
    assert result["dataset_kind"] == "human" and result["study_freeze_sha256"]
    assert "Exploratory human" in (tmp_path / "accepted-fixture/REPORT.md").read_text()
    with (directory / "participant/form-X.txt").open("a") as stream:
        stream.write("Changed after freeze")
    with pytest.raises(ValueError, match="changed after freeze"):
        study.analyze_learning(directory, tmp_path / "changed")
    assert not (tmp_path / "changed").exists()


@pytest.mark.parametrize(
    "field,value", [("participant_id", "name@example.invalid"), ("minutes", "nan"), ("context_used", "yes")]
)
def test_learning_rejects_identifying_ids_and_invalid_values_before_writing(tmp_path, field, value):
    directory = tmp_path / "study"
    study.initialize(directory)
    learning_csv(directory)
    path = directory / "learning.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0][field] = value
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        study.analyze_learning(directory, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("collected", ["responses.json", "blind-key.json"])
def test_experiment_refuses_a_retrospective_first_freeze(tmp_path, collected):
    directory = tmp_path / "experiment"
    experiment.prepare(directory)
    experiment.write_json(directory / collected, [{"already": "collected"}], replace=True)
    with pytest.raises(ValueError, match="before collecting"):
        experiment.freeze(directory)
    assert not (directory / "freeze.json").exists()


def test_preparation_checks_serialized_collection_budget_before_creating_output(tmp_path, monkeypatch):
    monkeypatch.setattr(experiment, "INPUT_BYTES", 10000)
    with pytest.raises(ValueError, match="frozen-input byte budget"):
        experiment.prepare(tmp_path / "oversized")
    assert not (tmp_path / "oversized").exists()


def test_setup_permission_failure_preserves_prior_file_and_explains_recovery(tmp_path, monkeypatch, capsys):
    from repertorio import cli

    original_write = cli.write_private
    count = 0

    def fail_second(path, content):
        nonlocal count
        count += 1
        if count == 2:
            raise subprocess.CalledProcessError(1, "icacls")
        original_write(path, content)

    monkeypatch.setattr(cli, "write_private", fail_second)
    assert main(["--db", str(tmp_path / "db.sqlite3"), "setup", "--output", str(tmp_path / "partial")]) != 0
    error = capsys.readouterr().err
    assert "new --output" in error and "icacls" in error
    assert (tmp_path / "partial/claude.mcp.json").is_file()
    assert not (tmp_path / "db.sqlite3").exists()


def test_study_first_freeze_refuses_nonempty_usability_table(tmp_path):
    directory = tmp_path / "study"
    study.initialize(directory)
    declared_ready(directory)
    with (directory / "usability.csv").open("ab") as stream:
        stream.write(b"synthetic,already-recorded\r\n")
    with pytest.raises(ValueError, match="before recording"):
        study.freeze(directory)
    assert not (directory / "study-freeze.json").exists()
