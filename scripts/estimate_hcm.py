"""Hybrid choice model example using the processed Qualtrics data.

This script augments the simple multinomial logit specification with a latent
variable measured by binary indicators (e.g., Likert statements recoded to 0/1).
It expects two inputs:

1. The long-format alternatives file produced by ``scripts/process_qualtrics.py``
   (with an optional merged design file).
2. A respondent-level CSV with a ``respondent_id`` column and indicator columns
   (plus any structural variables you want to include in the latent variable).

The latent variable enters the utility of the second alternative (to avoid
identification issues) and is also linked to each indicator through a simple
logistic measurement equation. Measurement contributions are weighted so they
enter the likelihood only once per respondent.

Example run from the repository root::

    python scripts/estimate_hcm.py \
        --input processed/choices_long.csv \
        --indicators survey_indicators.csv \
        --indicator-cols ind_env ind_cost \
        --struct-vars age income \
        --output biogeme_hcm

The Biogeme output (HTML, pickle, synthetic results) will be placed inside the
requested directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import biogeme.biogeme as bio
from biogeme.expressions import Beta, Variable, bioLogLogit, log, exp, PanelLikelihoodTrajectory
import pandas as pd

CORE_COLUMNS = {"respondent_id", "task", "alternative", "chosen", "raw_choice"}


def build_wide_rows(df: pd.DataFrame, alt_order: Tuple[str, str]) -> pd.DataFrame:
    """Convert long-format alternatives into one row per task."""

    attribute_cols = [c for c in df.columns if c not in CORE_COLUMNS]
    records: List[Dict[str, object]] = []

    for (respondent, task), group in df.groupby(["respondent_id", "task"]):
        row: Dict[str, object] = {"respondent_id": respondent, "task": task}
        choice_code = None

        for alt_code in alt_order:
            alt_row = group.loc[group["alternative"] == alt_code]
            if alt_row.empty:
                continue

            alt_record = alt_row.iloc[0]
            if int(alt_record["chosen"]) == 1:
                choice_code = alt_code

            for attr in attribute_cols:
                row[f"{attr}_{alt_code}"] = alt_record.get(attr)

        if choice_code is None:
            continue

        row["choice_code"] = choice_code
        records.append(row)

    return pd.DataFrame.from_records(records)


def merge_indicator_data(
    df_wide: pd.DataFrame, indicators_path: Path, struct_vars: Sequence[str], indicator_cols: Sequence[str] | None
) -> Tuple[pd.DataFrame, List[str]]:
    """Attach respondent-level indicators and return the merged frame and detected indicators."""

    indicators = pd.read_csv(indicators_path)
    if "respondent_id" not in indicators.columns:
        raise ValueError("Indicator file must contain a respondent_id column.")

    missing_struct = [c for c in struct_vars if c not in indicators.columns]
    if missing_struct:
        raise ValueError(f"Missing structural variables in indicators file: {missing_struct}")

    auto_indicator_cols: List[str] = []
    if indicator_cols:
        missing_indicators = [c for c in indicator_cols if c not in indicators.columns]
        if missing_indicators:
            raise ValueError(f"Indicator columns not found: {missing_indicators}")
        auto_indicator_cols = list(indicator_cols)
    else:
        auto_indicator_cols = [c for c in indicators.columns if c not in {"respondent_id", *struct_vars}]
        if not auto_indicator_cols:
            raise ValueError("No indicator columns detected. Provide --indicator-cols explicitly.")

    merged = df_wide.merge(indicators, on="respondent_id", how="inner")
    if merged.empty:
        raise ValueError("Merging indicators with choice data produced an empty dataset.")

    # Weight so each indicator contributes once per respondent
    merged["measurement_weight"] = merged.groupby("respondent_id")["task"].transform("nunique")
    merged["measurement_weight"] = 1.0 / merged["measurement_weight"]

    return merged, auto_indicator_cols


def build_hcm_model(
    df_wide: pd.DataFrame,
    alt_order: Tuple[str, str],
    indicator_cols: Iterable[str],
    struct_vars: Iterable[str],
) -> bio.BIOGEME:
    """Create a Biogeme HCM with a single latent variable and binary indicators."""

    alt_to_id = {code: idx + 1 for idx, code in enumerate(alt_order)}
    df_wide = df_wide.copy()
    df_wide["choice_id"] = df_wide["choice_code"].map(alt_to_id)

    database = bio.Database("qualtrics_hcm", df_wide)
    database.panel("respondent_id")

    choice_var = Variable("choice_id")
    meas_weight = Variable("measurement_weight")

    availability = {alt_to_id[code]: 1 for code in alt_order}
    asc_b = Beta("ASC_B", 0, None, None, 0)

    attribute_betas: Dict[str, Beta] = {}
    attribute_basenames = sorted(
        {col.rsplit("_", 1)[0] for col in df_wide.columns if "_" in col and col.split("_")[-1] in alt_order}
    )
    for attr in attribute_basenames:
        attribute_betas[attr] = Beta(f"B_{attr}", 0, None, None, 0)

    # Latent variable specification
    latent = Beta("LV_const", 0, None, None, 0)
    for sv in struct_vars:
        latent += Beta(f"LV_{sv}", 0, None, None, 0) * Variable(sv)

    beta_latent_b = Beta("B_LV_B", 0, None, None, 0)

    def utility_for_alt(code: str):
        util = 0
        if code == alt_order[1]:
            util += asc_b + beta_latent_b * latent
        for base, beta_param in attribute_betas.items():
            column_name = f"{base}_{code}"
            if column_name in df_wide.columns:
                util += beta_param * Variable(column_name)
        return util

    utilities = {alt_to_id[code]: utility_for_alt(code) for code in alt_order}
    logprob_choice = bioLogLogit(utilities, availability, choice_var)

    # Measurement equations (binary logistic)
    measurement_terms = []
    for ind in indicator_cols:
        lambda_param = Beta(f"lambda_{ind}", 0, None, None, 0)
        delta_param = Beta(f"delta_{ind}", 0, None, None, 0)
        z = delta_param + lambda_param * latent
        prob = 1.0 / (1.0 + exp(-z))
        indicator_var = Variable(ind)
        measurement_terms.append(indicator_var * log(prob) + (1 - indicator_var) * log(1 - prob))

    if not measurement_terms:
        raise ValueError("At least one indicator is required for the HCM.")

    loglike_row = logprob_choice + meas_weight * sum(measurement_terms)
    loglike = PanelLikelihoodTrajectory(loglike_row)

    biogeme_model = bio.BIOGEME(database, loglike)
    biogeme_model.modelName = "qualtrics_hcm"
    return biogeme_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate a simple hybrid choice model.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("processed/choices_long.csv"),
        help="Path to the long-format CSV produced by process_qualtrics.py.",
    )
    parser.add_argument(
        "--indicators",
        type=Path,
        required=True,
        help="CSV with respondent_id plus indicator columns (and optional structural variables).",
    )
    parser.add_argument(
        "--indicator-cols",
        type=str,
        nargs="*",
        default=None,
        help="Indicator column names (binary). If omitted, all non-respondent/struct columns are used.",
    )
    parser.add_argument(
        "--struct-vars",
        type=str,
        nargs="*",
        default=(),
        help="Columns used in the latent variable structural equation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("biogeme_output_hcm"),
        help="Directory for Biogeme output files.",
    )
    parser.add_argument(
        "--alt-order",
        type=str,
        nargs=2,
        default=("A", "B"),
        metavar=("ALT1", "ALT2"),
        help="Alternative codes in preferred order (default: A B).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df_long = pd.read_csv(args.input)
    df_wide = build_wide_rows(df_long, tuple(args.alt_order))
    if df_wide.empty:
        raise ValueError("No valid observations found after reshaping to wide format.")

    df_merged, indicator_cols = merge_indicator_data(
        df_wide=df_wide,
        indicators_path=args.indicators,
        struct_vars=tuple(args.struct_vars),
        indicator_cols=args.indicator_cols,
    )

    biogeme_model = build_hcm_model(
        df_wide=df_merged,
        alt_order=tuple(args.alt_order),
        indicator_cols=indicator_cols,
        struct_vars=tuple(args.struct_vars),
    )

    args.output.mkdir(parents=True, exist_ok=True)
    results = biogeme_model.estimate(directory=args.output)

    print("Estimation completed. Summary:")
    print(results.getGeneralStatistics())


if __name__ == "__main__":
    main()
