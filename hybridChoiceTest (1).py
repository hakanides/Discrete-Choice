# ==============================================================================
# IMPORTS
# ==============================================================================
import biogeme.biogeme as bio
import numpy as np
import biogeme.models as models

from biogeme.expressions import (
    Beta,
    Variable,
    Draws,
    MonteCarlo,
    log,
    NormalCdf,
)

from data_preperation import (
    database,
    standard_duration,
    standard_price,
    paid1_duration,
    paid1_price,
    paid2_duration,
    paid2_price,
    chosen_alternative,
)
print("Missing values in database:")
print(database.dataframe.isna().sum())
cols_to_check = [
    'standard_duration', 'standard_price',
    'paid1_duration', 'paid1_price',
    'paid2_duration', 'paid2_price',
    'secularism 1', 'chosen_alternative'
]
database.dataframe.dropna(subset=cols_to_check, inplace=True)
cols_to_check = [
    'secularism 1',
    'chosen_alternative',
    'standard_duration', 'standard_price',
    'paid1_duration', 'paid1_price',
    'paid2_duration', 'paid2_price'
]
print("Checking for NaNs (Empty cells)...")
null_counts = database.dataframe[cols_to_check].isnull().sum()
if null_counts.sum() > 0:
    print("Found NaNs! Removing rows with missing data...")
    print(null_counts[null_counts > 0])
    database.dataframe.dropna(subset=cols_to_check, inplace=True)
else:
    print("No NaNs found. Data is clean.")

EPS = 1e-300
print(database.dataframe['chosen_alternative'].value_counts(dropna=False))
print(database.dataframe['secularism 1'].value_counts(dropna=False))
print(
    database.dataframe[['choice_A','choice_B','choice_C']].sum(axis=1).value_counts()
)


omega_sec = Draws("omega_sec", "NORMAL") #error
alpha_sec = Beta("alpha_sec", 0, None, None, 1)

# No demographics
#Secular = alpha_sec + omega_sec
Secular = omega_sec


Constant2 = Beta("Constant2", 0, None, None, 0)
Constant3 = Beta("Constant3", 0, None, None, 0)

Duration = Beta("Duration", 0, None, None, 0)
Price = Beta("Price", 0, None, None, 0)

lambda_sec = Beta("lambda_sec", 0, None, None, 0)

V1 = Duration * standard_duration + Price * standard_price

V2 = (
    Constant2
    + Duration * paid1_duration
    + Price * paid1_price
    + lambda_sec * Secular
)

V3 = (
    Constant3
    + Duration * paid2_duration
    + Price * paid2_price
    + lambda_sec * Secular
)

V = {1: V1, 2: V2, 3: V3}
av = {1: 1, 2: 1, 3: 1}

choice_prob = models.loglogit(V, av, chosen_alternative)


sec1 = Variable("secularism 1")

delta_sec = Beta("delta_sec", 1, None, None, 0)

# Ordered thresholds (incremental = safe)
mu1 = Beta("mu1", -1, None, None, 0)
d2 = Beta("d2", 1, 1e-5, None, 0)
d3 = Beta("d3", 1, 1e-5, None, 0)
d4 = Beta("d4", 1, 1e-5, None, 0)

mu2 = mu1 + d2
mu3 = mu2 + d3
mu4 = mu3 + d4

latent_term = delta_sec * Secular

P1 = NormalCdf(mu1 - latent_term)
P2 = NormalCdf(mu2 - latent_term) - NormalCdf(mu1 - latent_term)
P3 = NormalCdf(mu3 - latent_term) - NormalCdf(mu2 - latent_term)
P4 = NormalCdf(mu4 - latent_term) - NormalCdf(mu3 - latent_term)
P5 = 1 - NormalCdf(mu4 - latent_term)

meas = (
    (sec1 == 1) * P1
    + (sec1 == 2) * P2
    + (sec1 == 3) * P3
    + (sec1 == 4) * P4
    + (sec1 == 5) * P5
)

# ==============================================================================
# FULL LIKELIHOOD
# ==============================================================================
# Calculate Joint Probability: P(Choice) * P(Measurement)
# We calculate the average of this probability (integral), then take the Log
joint_prob = choice_prob * meas
simulated_prob = MonteCarlo(joint_prob)
log_likelihood = log(simulated_prob + EPS)

# ==============================================================================
# ESTIMATION
# ==============================================================================
biogeme = bio.BIOGEME(database, log_likelihood)
biogeme.model_name = "HCM_minimal_secular"
biogeme.numberOfDraws = 500


results = biogeme.estimate ()
print(results.short_summary())
