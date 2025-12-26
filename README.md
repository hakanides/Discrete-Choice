# Discrete Choice Data Preparation

This repository contains the raw Qualtrics export from the discrete choice
experiment and a helper script that reshapes the data into a Biogeme-friendly
long format.

## Preparing the environment

Install the Python dependencies locally (preferably inside a virtual
environment):

```bash
pip install -r requirements.txt
```

The pipeline uses pandas for reshaping. Biogeme is listed as well so that you
can move directly to model estimation after the preprocessing step.

## Usage

1. Place the Qualtrics CSV export in the repository root. The current sample
   file is `Test Giray_December 26, 2025_07.56.csv`.
2. (Optional) Prepare a design file that lists the attribute levels for each
   alternative in every choice task. It must have at least the columns
   `task` and `alternative`; additional columns (e.g., cost, time, policy
   scenario flags) will be preserved.
3. Run the processor script:

```bash
python scripts/process_qualtrics.py \
    --input "Test Giray_December 26, 2025_07.56.csv" \
    --output processed/choices_long.csv \
    --design design.csv
```

The output will contain one row per alternative per choice task with a binary
`chosen` flag and a `raw_choice` column that keeps the original Qualtrics
answer text. A small summary is printed to the console to confirm how many
responses were retained for each alternative.

## Estimating a Biogeme model

Once the long-format file is available, you can run a simple multinomial logit
specification with Biogeme:

```bash
python scripts/estimate_biogeme.py \
    --input processed/choices_long.csv \
    --output biogeme_output
```

The script reshapes the long data back to one row per task, maps alternatives A
and B to integer codes, and estimates an MNL with an alternative-specific
constant for B. Any design attributes merged earlier (e.g., cost or time)
become part of the utility specification automatically. The usual Biogeme
reports are written to the requested output directory.

### Notes on filtering

The script automatically removes preview submissions, unfinished responses, and
records with progress below 80%. You can change the progress threshold with the
`--min-progress` flag.

### Design file expectations

Because the Qualtrics export only stores the selected alternative text, the
attribute levels used in each choice situation need to come from the experimental
plan. The design file should follow the structure below:

| task | alternative | attribute_cost | attribute_time | ... |
| --- | --- | --- | --- | --- |
| 1 | A | 1000 | 6 | ... |
| 1 | B | 1500 | 4 | ... |
| 2 | A | ... | ... | ... |

This structure allows Biogeme to work with the alternative-level data once the
long-format file is created.
