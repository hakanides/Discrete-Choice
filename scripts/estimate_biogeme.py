"""Example Biogeme specification for the processed choice data.

This script loads the long-format CSV produced by ``scripts/process_qualtrics.py``
(spread over alternatives) and estimates a simple multinomial logit model. It
assumes the dataset contains two alternatives labelled ``A`` and ``B`` and that
any additional columns beyond the core identifiers correspond to alternative-
level attributes that were merged from the experimental design.

Run from the repository root after generating ``processed/choices_long.csv``::

    python scripts/estimate_biogeme.py \
        --input processed/choices_long.csv \
        --output biogeme_output

The output directory will contain the usual Biogeme report files (HTML, pickle,
and the synthetic estimation results object).
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import biogeme.biogeme as bio
from biogeme.expressions import Beta, Variable, bioLogLogit
import pandas as pd


CORE_COLUMNS = {"respondent_id", "task", "alternative", "chosen", "raw_choice"}


def build_wide_rows(df: pd.DataFrame, alt_order: Tuple[str, str]) -> pd.DataFrame:
    """Convert long-format alternatives into one row per task.

    Parameters
    ----------
    df:
        Long-format choices with columns ``respondent_id``, ``task``,
        ``alternative``, ``chosen``, and any number of design attributes.
    alt_order:
        Tuple of alternative codes in their preferred order, e.g., ("A", "B").

    Returns
    -------
    pd.DataFrame
        Wide table with one row per respondent-task, including a numeric
        ``choice_id`` column and attribute columns of the form
        ``{attribute}_{alt}``.
    """

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
            # Skip incomplete tasks that lack a marked choice
            continue

        row["choice_code"] = choice_code
        records.append(row)

    return pd.DataFrame.from_records(records)


def build_biogeme_model(df_wide: pd.DataFrame, alt_order: Tuple[str, str]) -> bio.BIOGEME:
    """Create a Biogeme object for a binary multinomial logit model."""

    alt_to_id = {code: idx + 1 for idx, code in enumerate(alt_order)}
    df_wide = df_wide.copy()
    df_wide["choice_id"] = df_wide["choice_code"].map(alt_to_id)

    database = bio.Database("qualtrics", df_wide)
    database.panel("respondent_id")

    choice_var = Variable("choice_id")

    # Always-on availability for both alternatives
    availability = {alt_to_id[code]: 1 for code in alt_order}

    # Parameter definitions (ASC for alt B only to avoid identification issues)
    asc_b = Beta("ASC_B", 0, None, None, 0)

    # Shared coefficients for each attribute (by base name)
    attribute_betas: Dict[str, Beta] = {}
    attribute_basenames = sorted({col.rsplit("_", 1)[0] for col in df_wide.columns if "_" in col and col.split("_")[-1] in alt_order})
    for attr in attribute_basenames:
        attribute_betas[attr] = Beta(f"B_{attr}", 0, None, None, 0)

    # Build utility functions per alternative
    def utility_for_alt(code: str):
        util = 0
        if code == alt_order[1]:
            util += asc_b

        for base, beta_param in attribute_betas.items():
            column_name = f"{base}_{code}"
            if column_name in df_wide.columns:
                util += beta_param * Variable(column_name)
        return util

    utilities = {alt_to_id[code]: utility_for_alt(code) for code in alt_order}

    logprob = bioLogLogit(utilities, availability, choice_var)
    biogeme_model = bio.BIOGEME(database, logprob)
    biogeme_model.modelName = "qualtrics_mnl"
    return biogeme_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate a simple Biogeme MNL model.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("processed/choices_long.csv"),
        help="Path to the long-format CSV produced by process_qualtrics.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("biogeme_output"),
        help="Directory for Biogeme output files (HTML, pickle, etc.).",
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

    biogeme_model = build_biogeme_model(df_wide, tuple(args.alt_order))
    args.output.mkdir(parents=True, exist_ok=True)
    results = biogeme_model.estimate(directory=args.output)

    print("Estimation completed. Summary:")
    print(results.getGeneralStatistics())


if __name__ == "__main__":
    main()
