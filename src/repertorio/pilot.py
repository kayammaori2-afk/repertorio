"""Pilot materials and synthetic-only demonstration of a preregistered analysis."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import Counter
from importlib.resources import files
from pathlib import Path
from typing import Any

SEED = 20261116
MAX_SCORE = 8


def synthetic_rows() -> list[dict[str, Any]]:
    """Block randomization within baseline strata. Outcomes are artificial fixtures."""
    rng = random.Random(SEED)
    rows = []
    number = 0
    for stratum in ("low", "high"):
        for block in range(6):
            allocation = list("ABC")
            rng.shuffle(allocation)
            for arm in allocation:
                number += 1
                baseline = 2 + block % 3 if stratum == "low" else 5 + block % 3
                # Deliberately mixed contrasts, missingness and protocol nonadherence.
                immediate = max(0, min(MAX_SCORE, baseline + {"A": 0, "B": 1, "C": 1}[arm] + (block % 3 - 1)))
                missing = (stratum, block, arm) in {("low", 2, "B"), ("high", 4, "C")}
                retention_missing = missing or (block == 1 and arm == "A")
                rows.append(
                    {
                        "dataset_kind": "synthetic",
                        "participant_id": f"S{number:03d}",
                        "stratum": stratum,
                        "block": f"{stratum}-{block}",
                        "arm": arm,
                        "baseline_score": baseline,
                        "immediate_form": "X" if block < 3 else "Y",
                        "retention_form": "Y" if block < 3 else "X",
                        "concept_order": "economics_first" if block % 2 == 0 else "probability_first",
                        "immediate_score": None if missing else immediate,
                        "retention_score": None if retention_missing else max(0, immediate - (block % 2)),
                        "missing_reason": "synthetic_withdrawal" if missing else "",
                        "retention_missing_reason": "synthetic_missed_followup" if retention_missing else "",
                        "minutes": None if missing else 15 + block % 4,
                        "hints": None if missing else block % 3,
                        "context_delivered": arm != "A",
                        "context_used": None if missing else arm != "A" and block != 3,
                        "conceptual_errors": None if missing else int(block % 3 == 0),
                        "error_codes": "" if missing or block % 3 != 0 else "P_DENOMINATOR",
                        "model": "NONE_SYNTHETIC",
                        "model_version": "NONE_SYNTHETIC",
                        "deviation": "synthetic_context_ignored" if arm != "A" and block == 3 else "",
                    }
                )
    return rows


def _validate(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("No pilot rows supplied")
    ids = [row["participant_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate participant IDs; one randomized participant is the analysis unit")
    kinds = {row["dataset_kind"] for row in rows}
    if len(kinds) != 1 or not kinds.issubset({"synthetic", "human"}):
        raise ValueError("Dataset must consistently identify synthetic or human provenance")
    for row in rows:
        if row["arm"] not in "ABC" or len(row["arm"]) != 1 or row["stratum"] not in ("low", "high"):
            raise ValueError("Invalid arm or baseline stratum")
        for field in ("baseline_score", "immediate_score", "retention_score"):
            value = row[field]
            if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= MAX_SCORE):
                raise ValueError(f"{field} must be missing or between 0 and {MAX_SCORE}")
        if row["baseline_score"] is None:
            raise ValueError("Baseline score is required before randomization")
        expected_stratum = "low" if row["baseline_score"] <= 4 else "high"
        if row["stratum"] != expected_stratum:
            raise ValueError("Baseline stratum must agree with the prespecified score threshold")
        if (
            row["immediate_form"] not in {"X", "Y"}
            or row["retention_form"] != {"X": "Y", "Y": "X"}[row["immediate_form"]]
        ):
            raise ValueError("Immediate form must be X/Y and retention must use the alternate form")
        if row["concept_order"] not in {"economics_first", "probability_first"}:
            raise ValueError("Unknown concept order")
        if row["immediate_score"] is None and not row["missing_reason"]:
            raise ValueError("Missing primary outcome requires a reason")
        if row["immediate_score"] is None and (
            any(row[field] is not None for field in ("minutes", "hints", "context_used", "conceptual_errors"))
            or row["error_codes"]
        ):
            raise ValueError(
                "Missing primary outcomes must not disclose artificial hidden outcome or process measures"
            )
        allowed_errors = {
            "E_FIXED_INCLUDED",
            "E_TOTAL_OR_AVERAGE",
            "E_COMPARISON",
            "P_DENOMINATOR",
            "P_NUMERATOR",
            "P_ARITHMETIC",
            "P_CONDITION_EXPLANATION",
        }
        error_codes = row["error_codes"].split("|") if row["error_codes"] else []
        if not set(error_codes).issubset(allowed_errors) or len(error_codes) != len(set(error_codes)):
            raise ValueError("Unknown or duplicate conceptual error category")
        if row["conceptual_errors"] is not None and row["conceptual_errors"] != len(error_codes):
            raise ValueError("Conceptual error count must equal distinct recorded categories")
        if row["retention_score"] is None and not row["retention_missing_reason"]:
            raise ValueError("Missing retention outcome requires a reason")
    if any(
        not any(row["arm"] == arm and row["stratum"] == stratum for row in rows)
        for arm in "ABC"
        for stratum in ("low", "high")
    ):
        raise ValueError("Each arm and baseline stratum needs at least one allocated participant")


def _standardized_difference(rows: list[dict[str, Any]], field: str) -> float | None:
    differences = []
    for stratum in ("low", "high"):
        values = {
            arm: [
                row[field]
                for row in rows
                if row["arm"] == arm and row["stratum"] == stratum and row[field] is not None
            ]
            for arm in "BC"
        }
        if not all(values.values()):
            return None
        differences.append(statistics.mean(values["C"]) - statistics.mean(values["B"]))
    return statistics.mean(differences)


def analyze(rows: list[dict[str, Any]], bootstrap_repetitions: int = 2000) -> dict[str, Any]:
    _validate(rows)
    if not 100 <= bootstrap_repetitions <= 10000:
        raise ValueError("Bootstrap repetitions must be between 100 and 10000")
    estimates = {}
    for field in ("immediate_score", "retention_score"):
        arm_stats = {}
        for arm in "ABC":
            allocated = [row for row in rows if row["arm"] == arm]
            observed = [row[field] for row in allocated if row[field] is not None]
            arm_stats[arm] = {
                "allocated": len(allocated),
                "observed": len(observed),
                "missing": len(allocated) - len(observed),
                "mean_observed": statistics.mean(observed) if observed else None,
            }
        estimate = _standardized_difference(rows, field)
        rng = random.Random(SEED)
        boot = []
        if estimate is not None:
            cells = [
                [
                    row
                    for row in rows
                    if row["arm"] == arm and row["stratum"] == stratum and row[field] is not None
                ]
                for arm in "BC"
                for stratum in ("low", "high")
            ]
            for _ in range(bootstrap_repetitions):
                sample = [rng.choice(cell) for cell in cells for _ in range(len(cell))]
                value = _standardized_difference(sample, field)
                if value is not None:
                    boot.append(value)
        boot.sort()
        bounds = {}
        for arm in "BC":
            stratum_bounds = []
            for stratum in ("low", "high"):
                cell = [row for row in rows if row["arm"] == arm and row["stratum"] == stratum]
                observed_sum = sum(row[field] for row in cell if row[field] is not None)
                missing = sum(row[field] is None for row in cell)
                stratum_bounds.append(
                    (observed_sum / len(cell), (observed_sum + MAX_SCORE * missing) / len(cell))
                )
            bounds[arm] = [statistics.mean(value[i] for value in stratum_bounds) for i in (0, 1)]
        estimates[field] = {
            "arms": arm_stats,
            "C_minus_B_complete_case_standardized": estimate,
            "bootstrap_95_percentile": [
                boot[int(0.025 * (len(boot) - 1))],
                boot[int(0.975 * (len(boot) - 1))],
            ]
            if boot
            else None,
            "all_allocated_missing_outcome_bounds": [
                bounds["C"][0] - bounds["B"][1],
                bounds["C"][1] - bounds["B"][0],
            ],
        }
    return {
        "dataset_kind": rows[0]["dataset_kind"],
        "participants": len(rows),
        "unit": "randomized_adult",
        "estimand": "C minus B equal-weight average of the low/high stratum-specific mean unassisted scores under allocation; not a sample-weighted population mean",
        "estimates": estimates,
        "bootstrap_repetitions": bootstrap_repetitions,
        "seed": SEED,
        "context_ignored": sum(row["context_delivered"] and row["context_used"] is False for row in rows),
        "context_use_missing": sum(row["context_used"] is None for row in rows),
        "form_by_arm_stratum": dict(
            sorted(Counter(f"{row['arm']}|{row['stratum']}|{row['immediate_form']}" for row in rows).items())
        ),
        "order_by_arm": dict(sorted(Counter(f"{row['arm']}|{row['concept_order']}" for row in rows).items())),
        "retention_form_by_arm": dict(
            sorted(Counter(f"{row['arm']}|{row['retention_form']}" for row in rows).items())
        ),
        "deviations": sum(bool(row["deviation"]) for row in rows),
        "interpretation": "Artificial data exercise analysis, attrition and implementation controls; they are not learning evidence."
        if rows[0]["dataset_kind"] == "synthetic"
        else "Exploratory pilot analysis; review consent, provenance, scoring and assumptions before interpretation.",
        "assumptions": "The complete-case estimate requires missingness independent of potential outcome within arm/stratum. "
        "Bounds require only scores in [0,8]. Percentile bootstrap resamples independent participants within arm/stratum; "
        "small cells and feasibility sampling limit inference. All participants remain assigned to randomized arms.",
    }


def analyze_csv(path: Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in (
            "baseline_score",
            "immediate_score",
            "retention_score",
            "minutes",
            "hints",
            "conceptual_errors",
        ):
            row[field] = float(row[field]) if row[field] != "" else None
        for field in ("context_delivered", "context_used"):
            if row[field] not in {"True", "False", ""}:
                raise ValueError(f"{field} must be True, False or missing")
            row[field] = row[field] == "True" if row[field] else None
    return analyze(rows)


def _write_analysis(output: Path, result: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    primary = result["estimates"]["immediate_score"]
    estimate = primary["C_minus_B_complete_case_standardized"]
    estimate_text = (
        "not estimable (empty observed arm/stratum cell)" if estimate is None else f"{estimate:.4f}/8"
    )
    (output / "REPORT.md").write_text(
        "# Pilot analysis demonstration\n\n"
        + result["interpretation"]
        + "\n\n"
        + f"Allocated: {result['participants']}. Primary all-allocated missing-outcome bounds (C−B, 0–8 score scale): "
        + f"{primary['all_allocated_missing_outcome_bounds']}.\n\n"
        + result["estimand"]
        + ".\n\n"
        + f"Form counts (arm|stratum|form): {result['form_by_arm_stratum']}. "
        + f"Concept order counts (arm|order): {result['order_by_arm']}.\n\n"
        + "Secondary assumption-dependent complete-case difference: "
        + estimate_text
        + ". "
        + f"Bootstrap interval: {primary['bootstrap_95_percentile']}. "
        + "\n\n"
        + result["assumptions"]
        + "\n",
        encoding="utf-8",
    )


def pilot(output: Path) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = synthetic_rows()
    (output / "pilot_items.json").write_bytes(
        files("repertorio").joinpath("data/pilot_items.json").read_bytes()
    )
    with (output / "synthetic.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = analyze(rows)
    _write_analysis(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze a pilot CSV or generate artificial analysis fixtures"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    arguments = parser.parse_args()
    if arguments.input:
        _write_analysis(arguments.output, analyze_csv(arguments.input))
    else:
        pilot(arguments.output)
