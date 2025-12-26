"""Utility to convert Qualtrics discrete choice data into a Biogeme-ready format.

This script assumes the Qualtrics export keeps the default two metadata rows
and uses a third row that stores the `ImportId` for each question. Only the
response rows are retained in the output.

Example usage:
    python scripts/process_qualtrics.py \
        --input "Test Giray_December 26, 2025_07.56.csv" \
        --output processed/choices_long.csv \
        --design design.csv

The optional design file must contain one row per alternative per scenario with
at least the columns `task` and `alternative`. Any additional columns (e.g.,
attribute levels) are merged onto the long-format data to make it ready for
Biogeme estimation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


@dataclass
class ProcessingConfig:
    """Configuration for Qualtrics -> Biogeme reshaping."""

    choice_prefix: str = "CE"
    choice_header_keywords: Tuple[str, ...] = ("Seçim", "Answer")
    alternatives: Tuple[str, str] = ("Seçenek A", "Seçenek B")
    respondent_id_column: str = "ResponseId"
    finished_column: str = "Finished"
    status_column: str = "Status"
    progress_column: str = "Progress"
    minimum_progress: int = 80

    def alternative_map(self) -> Dict[str, str]:
        """Mapping from raw labels to short alternative codes.

        The tuple order is respected, so the first entry is coded as "A" and
        the second entry as "B". The mapping is case-sensitive to avoid
        unexpected matches when new alternatives are added later.
        """

        return {label: code for label, code in zip(self.alternatives, ("A", "B"))}


def load_qualtrics(input_path: Path, config: ProcessingConfig) -> pd.DataFrame:
    """Load the Qualtrics CSV while skipping metadata rows."""

    df = pd.read_csv(input_path, skiprows=[1, 2])
    df.columns = [col.strip() for col in df.columns]
    return df


def filter_responses(df: pd.DataFrame, config: ProcessingConfig) -> pd.DataFrame:
    """Remove preview/incomplete responses and enforce minimum progress."""

    cleaned = df.copy()
    if config.finished_column in cleaned.columns:
        cleaned = cleaned[cleaned[config.finished_column] == True]  # noqa: E712

    if config.status_column in cleaned.columns:
        cleaned = cleaned[cleaned[config.status_column] != "Survey Preview"]

    if config.progress_column in cleaned.columns:
        cleaned[config.progress_column] = pd.to_numeric(
            cleaned[config.progress_column], errors="coerce"
        )
        cleaned = cleaned[cleaned[config.progress_column] >= config.minimum_progress]

    cleaned = cleaned.reset_index(drop=True)
    return cleaned


def find_choice_columns(df: pd.DataFrame, config: ProcessingConfig) -> List[str]:
    """Identify the columns that correspond to discrete-choice responses."""

    choice_cols: List[str] = []
    for col in df.columns:
        if not col.startswith(config.choice_prefix):
            continue
        if any(keyword in col for keyword in config.choice_header_keywords):
            choice_cols.append(col)

    return choice_cols


def reshape_to_long(
    df: pd.DataFrame, choice_cols: Iterable[str], config: ProcessingConfig
) -> pd.DataFrame:
    """Convert wide-format Qualtrics choices to a long Biogeme table."""

    alt_map = config.alternative_map()
    records = []

    for _, row in df.iterrows():
        respondent_id = row.get(config.respondent_id_column)
        for col in choice_cols:
            raw_choice = row[col]
            if pd.isna(raw_choice):
                continue

            # Extract task number by stripping the prefix and trailing text
            task_number = col.replace(config.choice_prefix, "").split()[0]

            for alt_label, alt_code in alt_map.items():
                records.append(
                    {
                        "respondent_id": respondent_id,
                        "task": int(task_number),
                        "alternative": alt_code,
                        "chosen": int(raw_choice == alt_label),
                        "raw_choice": raw_choice,
                    }
                )

    long_df = pd.DataFrame.from_records(records)
    return long_df


def merge_design(long_df: pd.DataFrame, design_path: Path) -> pd.DataFrame:
    """Merge experimental design attributes onto the long-format choices."""

    design_df = pd.read_csv(design_path)
    required_cols = {"task", "alternative"}
    missing = required_cols - set(design_df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Design file is missing required columns: {missing_cols}")

    merged = long_df.merge(design_df, on=["task", "alternative"], how="left")
    return merged


def summarize(long_df: pd.DataFrame) -> pd.DataFrame:
    """Provide quick counts to verify the reshaping step."""

    summary = (
        long_df.groupby(["task", "alternative"])  # type: ignore[call-arg]
        .agg(n=("chosen", "size"), choices=("chosen", "sum"))
        .reset_index()
    )
    return summary


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Qualtrics discrete choice data for Biogeme.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the Qualtrics CSV export.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("processed/choices_long.csv"),
        help="Where to write the long-format choices (CSV).",
    )
    parser.add_argument(
        "--design",
        type=Path,
        default=None,
        help=(
            "Optional path to a design file with columns [task, alternative, ...] "
            "to append attribute levels."
        ),
    )
    parser.add_argument(
        "--min-progress",
        type=int,
        default=80,
        help="Minimum progress percentage to retain a response (default: 80).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    config = ProcessingConfig(minimum_progress=args.min_progress)

    raw_df = load_qualtrics(args.input, config)
    cleaned_df = filter_responses(raw_df, config)
    choice_cols = find_choice_columns(cleaned_df, config)

    if not choice_cols:
        raise ValueError("No choice columns were found. Check the prefix/keywords.")

    long_df = reshape_to_long(cleaned_df, choice_cols, config)

    if args.design is not None:
        long_df = merge_design(long_df, args.design)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(args.output, index=False)

    summary_df = summarize(long_df)
    print("Saved long-format choices to", args.output)
    print("\nChoice counts by task and alternative:")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
