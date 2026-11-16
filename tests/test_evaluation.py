import re
from copy import deepcopy

import pytest

from repertorio.evaluation import arms, audit_diagnostics, evaluate, load_data, ndcg, oracle_eligible
from repertorio.pilot import _write_analysis, analyze, analyze_csv, pilot, synthetic_rows
from repertorio.selection import candidate_pool, catalog


def test_ndcg_accounts_for_missing_and_ineligible_gold():
    assert ndcg([], {"good": 3}) == 0
    assert ndcg(["good"], {"good": 3}) == 1
    assert ndcg(["bad", "good"], {"good": 3, "bad": 0}) == pytest.approx(1 / 1.584962500721156)
    assert ndcg([], {}) is None


def test_equal_candidate_ablation_and_identical_academic_package():
    for case in load_data("benchmark.json")["cases"]:
        outputs = arms(case)
        assert all(outputs[arm]["academic_package"] == outputs["A"]["academic_package"] for arm in "BCD")
        pool, _ = candidate_pool(case["profile"], case["concept"])
        assert len(outputs["D"]["references"]) == min(3, len(pool))
        assert len(outputs["C"]["references"]) == min(3, len(pool))
        assert all(ref["id"] in {r["id"] for r in pool} for ref in outputs["D"]["references"])


def test_independent_oracle_detects_a_deliberately_unsafe_reference():
    case = next(c for c in load_data("benchmark.json")["cases"] if c["id"] == "spoiler-blocked")
    reference = next(r for r in catalog()["references"] if r["id"] == "oc-story")
    assert not oracle_eligible(case, reference)


def test_evaluation_twice_is_semantically_byte_identical(tmp_path):
    result = evaluate(tmp_path / "first")
    assert result == evaluate(tmp_path / "second")
    for name in (
        "results.json",
        "summary.json",
        "pairs.json",
        "contexts.json",
        "results.csv",
        "manifest.json",
        "diagnostics.json",
        "REPORT.md",
    ):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()
    assert result["arms"]["A"]["mean_ndcg_at_3"] is None
    assert all(stat["constraint_violations"] == 0 for stat in result["arms"].values())
    assert result["B_wins"]  # Retain real countercases; no gate requires C to outperform.


def test_changed_input_manifest_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr("repertorio.evaluation.input_hashes", lambda: {"changed": "hash"})
    with pytest.raises(ValueError, match="Frozen"):
        evaluate(tmp_path)


def test_pilot_missingness_and_reanalysis_are_explicit(tmp_path):
    result = pilot(tmp_path)
    assert result == analyze_csv(tmp_path / "synthetic.csv")
    assert result["dataset_kind"] == "synthetic"
    assert result["participants"] == 36
    primary = result["estimates"]["immediate_score"]
    assert sum(arm["missing"] for arm in primary["arms"].values()) == 2
    assert sum(arm["allocated"] for arm in primary["arms"].values()) == 36
    bounds = primary["all_allocated_missing_outcome_bounds"]
    assert bounds[0] <= bounds[1]
    assert result["context_ignored"] > 0


def test_pilot_rejects_duplicate_ids_mislabeled_data_and_unexplained_missingness():
    rows = synthetic_rows()
    with pytest.raises(ValueError, match="Duplicate"):
        analyze(rows + [rows[0]])
    bad = deepcopy(rows)
    bad[0]["dataset_kind"] = "human"
    with pytest.raises(ValueError, match="provenance"):
        analyze(bad)
    bad = deepcopy(rows)
    bad[0].update(immediate_score=None, missing_reason="")
    with pytest.raises(ValueError, match="requires a reason"):
        analyze(bad)


def test_pilot_all_missing_cell_has_no_point_estimate(tmp_path):
    rows = synthetic_rows()
    for row in rows:
        if row["stratum"] == "low" and row["arm"] == "C":
            row.update(
                immediate_score=None,
                missing_reason="synthetic_withdrawal",
                minutes=None,
                hints=None,
                context_used=None,
                conceptual_errors=None,
                error_codes="",
            )
    result = analyze(rows)
    assert result["estimates"]["immediate_score"]["C_minus_B_complete_case_standardized"] is None
    _write_analysis(tmp_path, result)
    assert "not estimable" in (tmp_path / "REPORT.md").read_text(encoding="utf-8")


def test_pilot_rejects_empty_cohort_and_mismatched_stratum():
    with pytest.raises(ValueError, match="No pilot rows"):
        analyze([])
    rows = synthetic_rows()
    rows[0]["stratum"] = "high"
    with pytest.raises(ValueError, match="stratum must agree"):
        analyze(rows)


def test_pilot_forms_orders_and_missingness_are_validated():
    rows = synthetic_rows()
    result = analyze(rows)
    assert set(result["order_by_arm"].values()) == {6}
    assert set(result["form_by_arm_stratum"].values()) == {3}
    bad = deepcopy(rows)
    bad[0]["retention_form"] = bad[0]["immediate_form"]
    with pytest.raises(ValueError, match="alternate"):
        analyze(bad)
    bad = deepcopy(rows)
    next(row for row in bad if row["immediate_score"] is None)["conceptual_errors"] = 2
    with pytest.raises(ValueError, match="hidden outcome"):
        analyze(bad)


def test_pilot_bank_separates_literal_exposure_from_test():
    bank = load_data("pilot_items.json")
    exposed = " ".join(
        " ".join(ref["mapping"]) + " " + ref["diagnostic"] + " " + ref["transfer"]
        for ref in catalog()["references"]
    )
    exposed += " " + " ".join(lesson["text"] for lesson in bank["shared_lessons"])
    numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", exposed))
    for item in bank["items"]:
        assert not re.search(r"[^\W\d_]\d|\d[^\W\d_]", item["prompt"]), item["id"]
        assert not numbers.intersection(re.findall(r"\b\d+(?:\.\d+)?\b", item["prompt"])), item["id"]
        assert not any(
            re.search(r"\b" + re.escape(keyword) + r"\b", exposed, re.IGNORECASE)
            for keyword in item["context_keywords"]
        ), item["id"]


def test_diagnostics_disclose_ties_and_dependence_without_changing_rankings():
    diagnostics = audit_diagnostics(load_data("benchmark.json")["cases"], 20)
    assert diagnostics == audit_diagnostics(load_data("benchmark.json")["cases"], 20)
    assert diagnostics["B_all_affinities_tied_cases"] > 0
    assert diagnostics["fit_grade_spearman_mean"] is not None
    assert diagnostics["distinct_objective_eligible_grade_setups"] < diagnostics["ranked_cases"]
    assert diagnostics["C_random_tie_mean_ndcg"] is not None
    assert set(diagnostics["cuts"]["fit_scenario"]) == {"baseline_strength", "other"}
    assert set(diagnostics["cuts"]["split"]) == {"development", "test"}


def test_pilot_answer_keys_match_visible_quantities():
    for item in load_data("pilot_items.json")["items"]:
        quantities = [int(number) for number in re.findall(r"\b\d+\b", item["prompt"])]
        answer = item["answer"]
        if item["concept"] == "marginal_analysis":
            assert quantities[3] == quantities[1] + 1
            assert answer["incremental_cost"] == quantities[4] - quantities[2]
            assert answer["incremental_benefit"] == quantities[5]
            assert answer["net"] == answer["incremental_benefit"] - answer["incremental_cost"]
            assert answer["decision"] == ("accept" if answer["net"] > 0 else "decline")
        else:
            assert answer["numerator"] == quantities[2]
            assert answer["denominator"] == quantities[1]
            assert answer["value"] == pytest.approx(answer["numerator"] / answer["denominator"])


def test_explicit_safety_fixture_detects_violation_even_if_consistency_oracle_fails(tmp_path, monkeypatch):
    def unsafe_arms(case):
        outputs = arms(case)
        if case["id"] == "spoiler-blocked":
            outputs["C"]["references"] = [{"id": "oc-story"}]
        return outputs

    monkeypatch.setattr("repertorio.evaluation.arms", unsafe_arms)
    monkeypatch.setattr("repertorio.evaluation.oracle_eligible", lambda case, reference: True)
    with pytest.raises(AssertionError, match="Hard-constraint"):
        evaluate(tmp_path)
