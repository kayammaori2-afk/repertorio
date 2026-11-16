"""Reproducible, explicitly internal offline comparison of context policies."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import re
import statistics
import time
from importlib.resources import files
from pathlib import Path
from typing import Any

from .selection import (
    MAX_CONTEXT_BYTES,
    candidate_pool,
    canonical_bytes,
    catalog,
    context_package,
    prepare_context,
    render_reference,
    score_reference,
)


def load_data(name: str) -> dict[str, Any]:
    return json.loads(files("repertorio").joinpath("data", name).read_text(encoding="utf-8"))


def input_hashes() -> dict[str, str]:
    paths = [
        "selection.py",
        "evaluation.py",
        "data/catalog.json",
        "data/benchmark.json",
        "data/preregistration.json",
        "pilot.py",
        "data/pilot_items.json",
        "data/freeze_history_v1.json",
    ]
    return {
        path: hashlib.sha256(files("repertorio").joinpath(path).read_bytes()).hexdigest() for path in paths
    }


def ndcg(ranking: list[str], grades: dict[str, int], k: int = 3) -> float | None:
    ideal = sorted(grades.values(), reverse=True)[:k]
    denominator = sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(ideal))
    if not denominator:
        return None
    numerator = sum(
        (2 ** grades.get(reference, 0) - 1) / math.log2(rank + 2)
        for rank, reference in enumerate(ranking[:k])
    )
    return numerator / denominator


def oracle_eligible(case: dict[str, Any], reference: dict[str, Any]) -> bool:
    """Consistency check duplicating policy gates; not an independent safety oracle."""
    for item in case["profile"]["repertoire"]:
        if item["id"] != reference["item_id"] or reference["concept"] != case["concept"]:
            continue
        if item.get("excluded") or item.get("status", "unknown") in ("planned", "unknown"):
            return False
        if item.get("familiarity", 0) < reference["required_familiarity"]:
            return False
        if any(element not in item.get("elements", []) for element in reference["required_elements"]):
            return False
        if reference.get("edition") is not None and item.get("edition") != reference["edition"]:
            return False
        for field, threshold in (
            ("progress", reference.get("required_progress", 0)),
            ("spoiler_limit", reference.get("spoiler_position", 0)),
        ):
            if threshold > 0 and (item.get(field) is None or item[field] < threshold):
                return False
        return True
    return False


def arms(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile, concept = case["profile"], case["concept"]
    candidates, rejected = candidate_pool(profile, concept)
    query = set(re.findall(r"[a-z0-9_]+", case["objective"].casefold())) | set(case["tags"])
    items = {item["id"]: item for item in profile["repertoire"]}
    # Favorites pass the SAME hard gates before they can be supplied. Up to five favorite
    # items are made available, then references are ordered only by affinity and stable ID.
    safe_item_ids = {
        reference["item_id"]
        for known_concept in catalog()["concepts"]
        for reference in candidate_pool(profile, known_concept)[0]
    }
    favorite_ids = [
        item["id"]
        for item in sorted(
            (item for item in profile["repertoire"] if item["id"] in safe_item_ids),
            key=lambda item: (-item["affinity"], item["id"]),
        )[:5]
    ]
    favorites = sorted(
        (reference for reference in candidates if reference["item_id"] in favorite_ids),
        key=lambda reference: (
            -items[reference["item_id"]]["affinity"],
            reference["item_id"],
            reference["id"],
        ),
    )
    tags_only = sorted(
        candidates,
        key=lambda reference: (
            -len(query.intersection(reference["tags"])),
            reference["id"],
        ),
    )
    a = context_package(profile, concept, [], [], "academic-only-v1")
    a["learner"]["repertoire_count"] = 0
    result = {
        "A": a,
        "B": context_package(
            profile,
            concept,
            [
                render_reference(
                    reference,
                    {
                        "order": "affinity descending, item id, reference id",
                        "affinity": items[reference["item_id"]]["affinity"],
                    },
                )
                for reference in favorites[:3]
            ],
            rejected,
            "favorites-v1",
        ),
        "C": prepare_context(profile, concept, case["objective"], case["tags"], 3),
        "D": context_package(
            profile,
            concept,
            [
                render_reference(
                    reference,
                    {
                        "order": "tag overlap descending, reference id",
                        "overlap": len(query.intersection(reference["tags"])),
                    },
                )
                for reference in tags_only[:3]
            ],
            rejected,
            "tags-ablation-v1",
        ),
    }
    result["B"]["favorite_item_ids"] = favorite_ids
    # The academic material and maximum budget are identical; the selector's extra
    # repertoire changes context length, never the maximum allowed length.
    academic = {"concept": concept, "objective": case["objective"], "evidence": profile["evidence"]}
    for package in result.values():
        package["academic_package"] = academic
    return result


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 8) if values else None


def _average_ranks(values: list[int]) -> list[float]:
    return [1 + sum(other < value for other in values) + (values.count(value) - 1) / 2 for value in values]


def _rank_correlation(left: list[int], right: list[int]) -> float | None:
    if len(left) < 2 or len(set(left)) < 2 or len(set(right)) < 2:
        return None
    return statistics.correlation(_average_ranks(left), _average_ranks(right))


def audit_diagnostics(cases: list[dict[str, Any]], repetitions: int = 200) -> dict[str, Any]:
    """Post-result diagnostics. Random tie priorities never consult grades."""
    diagnostics = []
    signatures: set[bytes] = set()
    for case in cases:
        candidates, _ = candidate_pool(case["profile"], case["concept"])
        grades = {ref["id"]: case["grades"].get(ref["id"], {}).get("grade", 0) for ref in candidates}
        if not any(grades.values()):
            continue
        signatures.add(
            canonical_bytes({"objective": case["objective"], "eligible": sorted(grades), "grades": grades})
        )
        fit = [reference["conceptual_fit"] for reference in candidates]
        labels = [grades[reference["id"]] for reference in candidates]
        query = set(re.findall(r"[a-z0-9_]+", case["objective"].casefold())) | set(case["tags"])
        overlaps = {ref["id"]: len(query.intersection(ref["tags"])) for ref in candidates}
        safe_ids = {
            ref["item_id"]
            for concept in catalog()["concepts"]
            for ref in candidate_pool(case["profile"], concept)[0]
        }
        items = [item for item in case["profile"]["repertoire"] if item["id"] in safe_ids]
        affinities = {item["id"]: item["affinity"] for item in items}
        seed = 20261116 + int.from_bytes(hashlib.sha256(case["id"].encode()).digest()[:4], "big")
        rng = random.Random(seed)
        c_rng = random.Random(seed + 9173)
        scores = {
            ref["id"]: score_reference(ref, case["profile"], case["objective"], case["tags"])[0]
            for ref in candidates
        }
        fixed = arms(case)
        fixed_ndcg = {arm: ndcg([ref["id"] for ref in fixed[arm]["references"]], grades) for arm in "BCD"}
        assert fixed_ndcg["B"] is not None and fixed_ndcg["C"] is not None
        b_samples, c_samples, d_samples = [], [], []
        for _ in range(repetitions):
            item_priority = {item["id"]: rng.random() for item in items}
            favorite_ids = sorted(
                affinities, key=lambda item_id: (-affinities[item_id], item_priority[item_id])
            )[:5]
            b_ranking = sorted(
                (ref for ref in candidates if ref["item_id"] in favorite_ids),
                key=lambda ref: (-affinities[ref["item_id"]], item_priority[ref["item_id"]], ref["id"]),
            )
            ref_priority = {ref["id"]: rng.random() for ref in candidates}
            d_ranking = sorted(candidates, key=lambda ref: (-overlaps[ref["id"]], ref_priority[ref["id"]]))
            c_priority = {ref["id"]: c_rng.random() for ref in candidates}
            c_ranking = sorted(candidates, key=lambda ref: (-scores[ref["id"]], c_priority[ref["id"]]))
            b_value = ndcg([ref["id"] for ref in b_ranking[:3]], grades)
            c_value = ndcg([ref["id"] for ref in c_ranking[:3]], grades)
            d_value = ndcg([ref["id"] for ref in d_ranking[:3]], grades)
            assert b_value is not None and c_value is not None and d_value is not None
            b_samples.append(b_value)
            c_samples.append(c_value)
            d_samples.append(d_value)
        diagnostics.append(
            {
                "case_id": case["id"],
                "split": case["split"],
                "concept": case["concept"],
                "fit_scenario": "baseline_strength" if case["scenario"] == "baseline_strength" else "other",
                "fixed_order_C_minus_B": fixed_ndcg["C"] - fixed_ndcg["B"],
                "fit_grade_spearman": _rank_correlation(fit, labels),
                "fit_equals_grade": fit == labels,
                "B_all_affinities_tied": len(set(affinities.values())) <= 1,
                "D_all_tag_scores_tied": len(set(overlaps.values())) <= 1,
                "D_all_tag_scores_zero": all(value == 0 for value in overlaps.values()),
                "B_random_tie_mean_ndcg": _mean(b_samples),
                "C_random_tie_mean_ndcg": _mean(c_samples),
                "D_random_tie_mean_ndcg": _mean(d_samples),
                "B_random_tie_min_max": [min(b_samples), max(b_samples)],
                "C_random_tie_min_max": [min(c_samples), max(c_samples)],
                "D_random_tie_min_max": [min(d_samples), max(d_samples)],
            }
        )
    correlations = [row["fit_grade_spearman"] for row in diagnostics if row["fit_grade_spearman"] is not None]
    cuts: dict[str, dict[str, Any]] = {}
    for field in ("split", "fit_scenario", "concept"):
        cuts[field] = {}
        for value in sorted({row[field] for row in diagnostics}):
            group = [row for row in diagnostics if row[field] == value]
            correlated = [row for row in group if row["fit_grade_spearman"] is not None]
            cuts[field][value] = {
                "cases": len(group),
                "correlation_denominator": len(correlated),
                "fit_grade_spearman_mean": _mean([row["fit_grade_spearman"] for row in correlated]),
                "fit_equals_grade_count": sum(row["fit_equals_grade"] for row in correlated),
                "fixed_order_mean_C_minus_B": _mean([row["fixed_order_C_minus_B"] for row in group]),
                **{
                    f"{arm}_random_tie_mean_ndcg": _mean(
                        [row[f"{arm}_random_tie_mean_ndcg"] for row in group]
                    )
                    for arm in "BCD"
                },
                "random_tie_mean_C_minus_B": _mean(
                    [row["C_random_tie_mean_ndcg"] - row["B_random_tie_mean_ndcg"] for row in group]
                ),
            }
    return {
        "status": "post_result_diagnostic_not_preregistered_not_independent_validation",
        "random_tie_repetitions": repetitions,
        "random_tie_seed": 20261116,
        "description": "Only tie orders are randomized independently of grades; original affinities and score/labels are unchanged. "
        "Means are Monte Carlo sensitivity diagnostics, not replacement confirmatory results or independent labels.",
        "ranked_cases": len(diagnostics),
        "distinct_objective_eligible_grade_setups": len(signatures),
        "fit_grade_spearman_mean": _mean(correlations),
        "correlation_denominator": len(correlations),
        "fit_equals_grade_count": sum(
            row["fit_equals_grade"] for row in diagnostics if row["fit_grade_spearman"] is not None
        ),
        "cuts": cuts,
        "B_all_affinities_tied_cases": sum(row["B_all_affinities_tied"] for row in diagnostics),
        "D_all_tag_scores_tied_cases": sum(row["D_all_tag_scores_tied"] for row in diagnostics),
        "D_all_tag_scores_zero_cases": sum(row["D_all_tag_scores_zero"] for row in diagnostics),
        "B_random_tie_mean_ndcg": _mean([row["B_random_tie_mean_ndcg"] for row in diagnostics]),
        "C_random_tie_mean_ndcg": _mean([row["C_random_tie_mean_ndcg"] for row in diagnostics]),
        "D_random_tie_mean_ndcg": _mean([row["D_random_tie_mean_ndcg"] for row in diagnostics]),
        "documented_prior_use_in_benchmark": sum(bool(case["profile"]["sessions"]) for case in cases),
        "cases": diagnostics,
    }


def evaluate(output: Path) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frozen = load_data("frozen_manifest.json")
    actual = input_hashes()
    if frozen["sha256"] != actual:
        raise ValueError("Frozen evaluation inputs changed; review and version the manifest before a new run")
    dataset = load_data("benchmark.json")
    references = {reference["id"]: reference for reference in catalog()["references"]}
    rows: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    times: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        gold = {
            ref_id: value["grade"]
            for ref_id, value in case["grades"].items()
            if oracle_eligible(case, references[ref_id])
        }
        positive = {ref_id for ref_id, grade in gold.items() if grade > 0}
        start = time.perf_counter_ns()
        outputs = arms(case)
        times.append({"case_id": case["id"], "all_four_arms_ns": time.perf_counter_ns() - start})
        for arm, package in outputs.items():
            ids = [reference["id"] for reference in package["references"]]
            violations = [ref_id for ref_id in ids if not oracle_eligible(case, references[ref_id])]
            forbidden = set(ids).intersection(case.get("forbidden_reference_ids", []))
            size = len(canonical_bytes(package))
            if size > MAX_CONTEXT_BYTES:
                raise AssertionError(f"Context budget exceeded: {case['id']}/{arm}")
            rows.append(
                {
                    "case_id": case["id"],
                    "group_id": case["group_id"],
                    "split": case["split"],
                    "domain": case["domain"],
                    "scenario": case["scenario"],
                    "arm": arm,
                    "ranking": ids,
                    "eligible_positive_count": len(positive),
                    "ndcg_at_3": None if arm == "A" else ndcg(ids, gold),
                    "positive_recall": None
                    if arm == "A" or not positive
                    else len(positive.intersection(ids)) / len(positive),
                    "positive_recall_ceiling": None
                    if arm == "A" or not positive
                    else min(3, len(positive)) / len(positive),
                    "abstention": not ids,
                    "correct_abstention": None if arm == "A" else not ids and not positive,
                    "unwarranted_abstention": None if arm == "A" else not ids and bool(positive),
                    "constraint_violations": len(set(violations) | forbidden),
                    "explicit_forbidden_violations": len(forbidden),
                    "context_bytes": size,
                }
            )
        contexts.append({"case_id": case["id"], "contexts": outputs})

    arm_stats = {}
    for arm in "ABCD":
        subset = [row for row in rows if row["arm"] == arm]
        applicable = [row for row in subset if row["ndcg_at_3"] is not None]
        arm_stats[arm] = {
            "cases": len(subset),
            "ranking_denominator": len(applicable),
            "mean_ndcg_at_3": _mean([row["ndcg_at_3"] for row in applicable]),
            "mean_positive_recall": _mean(
                [row["positive_recall"] for row in subset if row["positive_recall"] is not None]
            ),
            "cases_with_context": sum(not row["abstention"] for row in subset),
            "correct_abstentions": None if arm == "A" else sum(row["correct_abstention"] for row in subset),
            "unwarranted_abstentions": None
            if arm == "A"
            else sum(row["unwarranted_abstention"] for row in subset),
            "constraint_violations": sum(row["constraint_violations"] for row in subset),
            "mean_context_bytes": round(statistics.mean(row["context_bytes"] for row in subset), 2),
            "max_context_bytes": max(row["context_bytes"] for row in subset),
        }
    paired = []
    for case in dataset["cases"]:
        by_arm = {row["arm"]: row for row in rows if row["case_id"] == case["id"]}
        if by_arm["C"]["ndcg_at_3"] is not None:
            paired.append(
                {
                    "case_id": case["id"],
                    "group_id": case["group_id"],
                    "split": case["split"],
                    "scenario": case["scenario"],
                    "C_minus_B": by_arm["C"]["ndcg_at_3"] - by_arm["B"]["ndcg_at_3"],
                    "C_minus_D": by_arm["C"]["ndcg_at_3"] - by_arm["D"]["ndcg_at_3"],
                }
            )
    slices = {}
    for field in ("split", "scenario", "group_id"):
        slices[field] = {
            value: {
                "denominator": len(group := [pair for pair in paired if pair[field] == value]),
                "mean_C_minus_B": _mean([pair["C_minus_B"] for pair in group]),
                "mean_C_minus_D": _mean([pair["C_minus_D"] for pair in group]),
            }
            for value in sorted({pair[field] for pair in paired})
        }
    summary = {
        "dataset_version": dataset["version"],
        "case_count": len(dataset["cases"]),
        "evidence_level": "internal_synthetic_selector_only",
        "arms": arm_stats,
        "paired_denominator": len(paired),
        "mean_C_minus_B": _mean([pair["C_minus_B"] for pair in paired]),
        "mean_C_minus_D": _mean([pair["C_minus_D"] for pair in paired]),
        "B_wins": [pair["case_id"] for pair in paired if pair["C_minus_B"] < -1e-12],
        "D_wins": [pair["case_id"] for pair in paired if pair["C_minus_D"] < -1e-12],
        "slices": slices,
        "report_version": "post-followup-v3",
        "equal_concept_group_mean_C_minus_B": _mean(
            [value for group in slices["group_id"].values() if (value := group["mean_C_minus_B"]) is not None]
        ),
        "limits": "Same agent authored catalog, cases and labels. No human or LLM efficacy evidence. "
        "Concept groups contain dependent variants. No statistical population inference or confidence interval.",
    }
    diagnostics = audit_diagnostics(dataset["cases"])
    summary["diagnostics"] = {key: value for key, value in diagnostics.items() if key != "cases"}
    for name, data in (
        ("results.json", rows),
        ("summary.json", summary),
        ("pairs.json", paired),
        ("contexts.json", contexts),
        ("manifest.json", frozen),
        ("latency.json", times),
        ("diagnostics.json", diagnostics),
    ):
        (output / name).write_bytes(canonical_bytes(data) + b"\n")
    (output / "environment.json").write_bytes(
        canonical_bytes(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "command": "repertorio evaluate --output DIR",
                "timing": "One warm-process local sequential pass; "
                "all four arms together in ns per case; includes context construction; excludes disk writes. "
                "Not an arm latency comparison. Timing is outside deterministic result artifacts.",
            }
        )
        + b"\n"
    )
    with (output / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({**row, "ranking": "|".join(row["ranking"])} for row in rows)
    report = [
        "# Internal offline evaluation",
        "",
        summary["limits"],
        "",
        (
            f"Primary fixed-ID-order held-out split: C−B = {slices['split']['test']['mean_C_minus_B']} "
            f"(n={slices['split']['test']['denominator']}); C does not beat B under that tie rule. "
            f"Equal-weight concept-group C−B = {summary['equal_concept_group_mean_C_minus_B']}. "
            f"The {len(paired)} ranked cases contain {diagnostics['distinct_objective_eligible_grade_setups']} distinct "
            "(objective, eligible-set, grade) setups; variants are dependent, and no fitting occurred."
        ),
        "",
        (
            "Timing of the original preregistration is author-asserted, not independently timestamped. "
            "Catalog judgments informed the same author's labels; non-baseline wins chiefly check consistency. "
            f"Mean fit/grade Spearman = {diagnostics['fit_grade_spearman_mean']}. "
            f"B has all-tied affinities in {diagnostics['B_all_affinities_tied_cases']}/{len(paired)} cases; "
            f"D has zero overlap in {diagnostics['D_all_tag_scores_zero_cases']}/{len(paired)}, making it ID order. "
            "Post-result random-tie diagnostics are in diagnostics.json; they do not repair label circularity."
        ),
        "",
        (
            "A has no ranking metric. B/C jointly compare repertoire availability and policy; C/D use "
            "the identical eligible candidate set and k=3. All arms share the academic package and 12,000-byte ceiling."
        ),
        "",
        "| Arm | nDCG@3 | Denominator | Contexts/cases | Violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm, stat in arm_stats.items():
        report.append(
            f"| {arm} | {stat['mean_ndcg_at_3']} | {stat['ranking_denominator']} | "
            f"{stat['cases_with_context']}/{stat['cases']} | {stat['constraint_violations']} |"
        )
    report += [
        "",
        (
            "Post-result tie sensitivity randomizes equal ordering scores in B, C and D; "
            "all non-tied policy scores remain fixed. Main results above retain the original stable-ID rule."
        ),
        "",
        "| Split | B random-tie nDCG | C random-tie nDCG | D random-tie nDCG | C−B | Cases |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for split, cut in diagnostics["cuts"]["split"].items():
        report.append(
            f"| {split} | {cut['B_random_tie_mean_ndcg']} | {cut['C_random_tie_mean_ndcg']} | "
            f"{cut['D_random_tie_mean_ndcg']} | {cut['random_tie_mean_C_minus_B']} | {cut['cases']} |"
        )
    fixed_test = slices["split"]["test"]["mean_C_minus_B"]
    randomized_test = diagnostics["cuts"]["split"]["test"]["random_tie_mean_C_minus_B"]
    sign_changed = fixed_test is not None and randomized_test is not None and fixed_test * randomized_test < 0
    report += [
        "",
        "The held-out C−B sign "
        + ("changes" if sign_changed else "does not change")
        + " under this seeded random-tie sensitivity analysis. Neither tie rule addresses shared-author "
        "label circularity; this is a post-result diagnostic, not a new confirmatory test.",
        "",
        (
            f"Fit equals grade in {diagnostics['fit_equals_grade_count']}/{diagnostics['correlation_denominator']} "
            "correlation-applicable cases. Correlation and the corresponding fixed-order C−B are separated below."
        ),
        "",
        "| Cut | Mean fit/grade rho | Rho n | Fixed C−B | Cases |",
        "|---|---:|---:|---:|---:|",
    ]
    for field in ("fit_scenario", "concept"):
        for name, cut in diagnostics["cuts"][field].items():
            report.append(
                f"| {field}: {name} | {cut['fit_grade_spearman_mean']} | {cut['correlation_denominator']} | "
                f"{cut['fixed_order_mean_C_minus_B']} | {cut['cases']} |"
            )
    report += [
        "",
        (
            f"Paired C−B: {summary['mean_C_minus_B']}; C−D: {summary['mean_C_minus_D']}; "
            f"n={len(paired)}. These are descriptive differences for constructed cases."
        ),
        "",
        "B wins: " + ", ".join(summary["B_wins"]),
        "D wins: " + ", ".join(summary["D_wins"]),
        "",
        (
            "Full case pairs, scenario/concept/split cuts, omission counts, context bytes and abstentions are in "
            "results.csv, pairs.json and summary.json. Latency is kept in latency.json with conditions in environment.json."
        ),
    ]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if any(stat["constraint_violations"] for stat in arm_stats.values()):
        raise AssertionError("Hard-constraint gate failed; see results.json")
    return summary
