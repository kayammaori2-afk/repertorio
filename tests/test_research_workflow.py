from __future__ import annotations

import csv
import json

import pytest

from repertorio import experiment, study
from repertorio.cli import main


def replace_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def prepared(tmp_path):
    source = tmp_path / "cases-input.json"
    replace_json(
        source,
        {
            "origin": "synthetic test fixture, no human labels",
            "cases": [
                {
                    "id": "case1",
                    "concept": "opportunity_cost",
                    "objective": "Explain opportunity cost",
                    "tags": [],
                    "group_id": "economics",
                    "profile": {"repertoire": [], "evidence": [], "sessions": []},
                },
                {
                    "id": "case2",
                    "concept": "conditional_probability",
                    "objective": "Explain conditional probability",
                    "tags": [],
                    "group_id": "probability",
                    "profile": {"repertoire": [], "evidence": [], "sessions": []},
                },
            ],
        },
    )
    directory = tmp_path / "experiment"
    experiment.prepare(directory, source)
    plan = experiment.read_json(directory / "plan.json")
    plan.update(provider="synthetic", model_version="fixture-1", case_author_ids=["author"])
    replace_json(directory / "plan.json", plan)
    experiment.freeze(directory)
    responses = [
        {
            "job_id": job["job_id"],
            "status": "completed",
            "dataset_kind": "synthetic_fixture",
            "provider": plan["provider"],
            "model_version": plan["model_version"],
            "generation_settings": plan["generation_settings"],
            "recorded_at": "2026-11-17T00:00:00Z",
            "text": "Synthetic response. No real tutor ran.",
        }
        for job in experiment.read_json(directory / "jobs.json")
    ]
    replace_json(directory / "responses.json", responses)
    return directory


def ratings(directory, output):
    key = experiment.read_json(directory / "blind-key.json")
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["response_id", "rater_id", "rater_kind", *experiment.METRICS, "rationale"]
        )
        writer.writeheader()
        for identifier in key["key"]:
            for rater in ("fixture-rater-a", "fixture-rater-b"):
                writer.writerow(
                    {
                        "response_id": identifier,
                        "rater_id": rater,
                        "rater_kind": "ai",
                        **dict.fromkeys(experiment.METRICS, 2),
                        "rationale": "Artificial test fixture",
                    }
                )


def test_prospective_packet_has_no_gold_or_conditions_and_preserves_real_empty_state(tmp_path):
    directory = tmp_path / "experiment"
    report = experiment.prepare(directory)
    assert report["jobs"] == 155
    assert experiment.read_json(directory / "responses.json") == []
    serialized = (directory / "jobs.json").read_text(encoding="utf-8")
    for forbidden in ('"grades"', '"conceptual_fit"', '"reason"', '"policy_version"', '"arm"'):
        assert forbidden not in serialized
    with pytest.raises(ValueError, match="provider"):
        experiment.freeze(directory)
    with pytest.raises(FileExistsError):
        experiment.prepare(directory)


def test_full_blinded_scoring_pipeline_is_labeled_synthetic_and_failures_preserved(tmp_path):
    directory = prepared(tmp_path)
    responses = experiment.read_json(directory / "responses.json")
    responses[0] = {
        "job_id": responses[0]["job_id"],
        "status": "failed",
        "dataset_kind": "synthetic_fixture",
        "failure_reason": "fixture_timeout",
    }
    replace_json(directory / "responses.json", responses)
    packet = tmp_path / "raters"
    result = experiment.blind(directory, packet)
    assert result["failed_jobs"] == 1
    assert not (packet / "blind-key.json").exists()
    assert "Synthetic response" in (packet / "responses-for-raters.json").read_text()
    sheet = tmp_path / "ratings.csv"
    ratings(directory, sheet)
    analysis = experiment.analyze(directory, sheet, tmp_path / "raters")
    assert analysis["dataset_kind"] == "synthetic_fixture"
    assert analysis["failed_jobs"]
    assert analysis["exact_criterion_agreement"] == 1
    assert analysis["contrasts"]["C_minus_E"]["equal_group_means"]["correctness"] == 0
    sheet.write_text(sheet.read_text().replace("fixture-rater-a", "author"))
    with pytest.raises(ValueError, match="independent"):
        experiment.analyze(directory, sheet, tmp_path / "raters")


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing", "every job"),
        ("duplicate", "every job"),
        ("metadata", "metadata"),
        ("kind", "consistently"),
    ],
)
def test_blinding_rejects_missing_duplicate_mixed_or_unmatched_responses(tmp_path, mutation, expected):
    directory = prepared(tmp_path)
    rows = experiment.read_json(directory / "responses.json")
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "metadata":
        rows[0]["model_version"] = "different-model"
    else:
        rows[0]["dataset_kind"] = "model_output"
    replace_json(directory / "responses.json", rows)
    with pytest.raises(ValueError, match=expected):
        experiment.blind(directory, tmp_path / "raters")
    assert not (tmp_path / "raters").exists()


def test_frozen_plan_and_post_blind_responses_cannot_be_silently_changed(tmp_path):
    directory = prepared(tmp_path)
    experiment.blind(directory, tmp_path / "raters")
    sheet = tmp_path / "ratings.csv"
    ratings(directory, sheet)
    rows = experiment.read_json(directory / "responses.json")
    rows[0]["text"] = "Changed after seeing ratings"
    replace_json(directory / "responses.json", rows)
    with pytest.raises(ValueError, match="changed after blinding"):
        experiment.analyze(directory, sheet, tmp_path / "raters")
    plan = experiment.read_json(directory / "plan.json")
    plan["model_version"] = "changed"
    replace_json(directory / "plan.json", plan)
    with pytest.raises(ValueError, match="Frozen inputs changed"):
        experiment.check_freeze(directory)


def test_study_empty_kit_blocks_readiness_and_has_no_answers_in_participant_forms(tmp_path, capsys):
    directory = tmp_path / "study"
    study.initialize(directory)
    assert study.check(directory)["pending"]
    assert main(["study", "check", "--directory", str(directory)]) == 3
    assert not json.loads(capsys.readouterr().out)["ready_by_operator_declarations"]
    with pytest.raises(ValueError, match="pending"):
        study.freeze(directory)
    with pytest.raises(ValueError, match="No observations"):
        study.analyze_usability(directory)
    for form in ("baseline", "X", "Y"):
        text = (directory / "participant" / f"form-{form}.txt").read_text(encoding="utf-8")
        assert "Resposta:" in text
        assert "incremental_cost" not in text and "Answer:" not in text
    assert (directory / "operator" / "item-bank-with-answers.json").exists()


def usability_fixture(directory):
    rows = []
    for person in ("p-0123456789abcdef", "p-fedcba9876543210"):
        for task in study.TASKS:
            rows.append(
                {
                    "dataset_kind": "synthetic",
                    "participant_id": person,
                    "task": task,
                    "completed": "True",
                    "assisted": "False",
                    "seconds": "12",
                    "failure_code": "",
                    "returned_within_7_days": "",
                }
            )
    return rows


def write_usability(directory, rows):
    with (directory / "usability.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=study.USABILITY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_usability_counts_all_enrolled_and_preserves_missingness(tmp_path):
    study.initialize(tmp_path / "study")
    directory = tmp_path / "study"
    rows = usability_fixture(directory)
    rows[0].update(completed="", assisted="", seconds="", failure_code="withdrawn")
    write_usability(directory, rows)
    result = study.analyze_usability(directory)
    assert result["dataset_kind"] == "synthetic"
    assert result["participants"] == 2 and result["return_unobserved"] == 2
    assert result["tasks"]["connect"]["completed_unassisted"] == 1
    assert result["tasks"]["connect"]["outcome_unobserved"] == 1
    rows.pop()
    write_usability(directory, rows)
    with pytest.raises(ValueError, match="all five"):
        study.analyze_usability(directory)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seconds", "nan"),
        ("seconds", "-1"),
        ("completed", "yes"),
        ("participant_id", "real-name"),
        ("dataset_kind", "human"),
    ],
)
def test_usability_invalid_data_or_unreviewed_human_data_is_rejected(tmp_path, field, value):
    directory = tmp_path / "study"
    study.initialize(directory)
    rows = usability_fixture(directory)
    for row in rows:
        row[field] = value
    write_usability(directory, rows)
    with pytest.raises(ValueError):
        study.analyze_usability(directory)


def test_declared_human_path_requires_unchanged_frozen_materials(tmp_path):
    # Artificial fixture exercises declarations only; no real consent/review exists.
    directory = tmp_path / "study"
    study.initialize(directory)
    protocol = experiment.read_json(directory / "study.json")
    protocol.update(dict.fromkeys(study.REQUIRED, "Artificial unit-test declaration"))
    protocol.update(dict.fromkeys(study.CONSENT_FIELDS, "Artificial unit-test declaration"))
    protocol.update(
        consent_text_reviewed=True, data_access_and_deletion_tested=True, recruitment_authorized=True
    )
    replace_json(directory / "study.json", protocol)
    consent = directory / "participant/consent-DRAFT.txt"
    assert main(["study", "consent", "--directory", str(directory)]) == 0
    assert study.check(directory)["ready_by_operator_declarations"]
    assert not study.check(directory)["human_reviews_verified_by_software"]
    study.freeze(directory)
    with pytest.raises(ValueError, match="frozen"):
        study.render_consent(directory)
    rows = usability_fixture(directory)
    for row in rows:
        row["dataset_kind"] = "human"  # Exercises claimed provenance, not an observed person.
    write_usability(directory, rows)
    assert study.analyze_usability(directory)["participants"] == 2
    consent.write_text("Changed after freeze", encoding="utf-8")
    with pytest.raises(ValueError, match="readiness declarations"):
        study.analyze_usability(directory)
    consent.write_text(study.consent_text(protocol), encoding="utf-8")
    with (directory / "participant/form-X.txt").open("a", encoding="utf-8") as stream:
        stream.write("Changed after freeze")
    with pytest.raises(ValueError, match="changed after freeze"):
        study.analyze_usability(directory)


def test_scoring_requires_two_complete_raters_and_disallows_missing_scores(tmp_path):
    directory = prepared(tmp_path)
    experiment.blind(directory, tmp_path / "raters")
    sheet = tmp_path / "ratings.csv"
    ratings(directory, sheet)
    with sheet.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows.pop()
    with sheet.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="same two"):
        experiment.analyze(directory, sheet, tmp_path / "raters")


@pytest.mark.parametrize("target", ["assignment", "provenance", "failed", "packet", "objective", "rubric"])
def test_analysis_rejects_post_blind_tampering(tmp_path, target):
    directory = prepared(tmp_path)
    packets = tmp_path / "raters"
    experiment.blind(directory, packets)
    sheet = tmp_path / "ratings.csv"
    ratings(directory, sheet)
    key_path = directory / "blind-key.json"
    key = experiment.read_json(key_path)
    if target == "assignment":
        ids = list(key["key"])
        key["key"][ids[0]], key["key"][ids[1]] = key["key"][ids[1]], key["key"][ids[0]]
        replace_json(key_path, key)
    elif target == "provenance":
        key["dataset_kind"] = "model_output"
        replace_json(key_path, key)
    elif target == "failed":
        key["failed"] = ["invented-failure"]
        replace_json(key_path, key)
    else:
        name = {
            "packet": "responses-for-raters.json",
            "objective": "objectives.json",
            "rubric": "RUBRIC.json",
        }[target]
        replace_json(packets / name, {"altered": True})
    with pytest.raises(ValueError, match="changed after blinding"):
        experiment.analyze(directory, sheet, packets)


def test_rubric_is_frozen_before_responses_and_cannot_change(tmp_path):
    directory = prepared(tmp_path)
    rubric = experiment.read_json(directory / "rubric.json")
    rubric["criteria"]["correctness"] = "Award full marks to any response"
    replace_json(directory / "rubric.json", rubric)
    with pytest.raises(ValueError, match="Frozen inputs changed"):
        experiment.blind(directory, tmp_path / "raters")


def test_full_supported_collection_size_is_readable(tmp_path):
    directory = prepared(tmp_path)
    rows = experiment.read_json(directory / "responses.json")
    # Ten legal strings with non-BMP JSON escaping exceed the former 8 MB cap.
    # Exercise 100 cases/500 responses with ASCII to stay modest in memory/time.
    source = experiment.read_json(directory / "cases.json")
    case = source["cases"][0]
    source["cases"] = [{**case, "id": f"case{i}"} for i in range(100)]
    case_path = tmp_path / "large-cases.json"
    replace_json(case_path, source)
    large = tmp_path / "large"
    experiment.prepare(large, case_path)
    plan = experiment.read_json(directory / "plan.json")
    replace_json(large / "plan.json", plan)
    experiment.freeze(large)
    responses = [
        {**rows[0], "job_id": job["job_id"], "text": "x" * 20000}
        for job in experiment.read_json(large / "jobs.json")
    ]
    replace_json(large / "responses.json", responses)
    assert (large / "responses.json").stat().st_size > 8_000_000
    assert len(experiment.response_materials(large, plan)["packets"]) == 500


def test_blank_consent_is_not_complete(tmp_path):
    directory = tmp_path / "study"
    study.initialize(directory)
    (directory / "participant/consent-DRAFT.txt").write_text("  \n", encoding="utf-8")
    assert "complete_and_review_participant_consent" in study.check(directory)["pending"]


def test_arbitrary_consent_text_cannot_substitute_required_fields(tmp_path):
    directory = tmp_path / "study"
    study.initialize(directory)
    (directory / "participant/consent-DRAFT.txt").write_text("Just a nonblank string", encoding="utf-8")
    assert "complete_required_consent_fields" in study.check(directory)["pending"]
    with pytest.raises(ValueError, match="consent field"):
        study.render_consent(directory)
    protocol = experiment.read_json(directory / "study.json")
    protocol.update(dict.fromkeys(study.CONSENT_FIELDS, "Synthetic content for tests"))
    replace_json(directory / "study.json", protocol)
    assert "render_consent_from_current_fields" in study.check(directory)["pending"]
    study.render_consent(directory)
    assert "render_consent_from_current_fields" not in study.check(directory)["pending"]
    protocol["provider"] = "Changed synthetic provider"
    replace_json(directory / "study.json", protocol)
    assert "render_consent_from_current_fields" in study.check(directory)["pending"]
