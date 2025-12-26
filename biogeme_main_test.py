# biogeme_main_test.py
import importlib.metadata
import biogeme.biogeme as bio
from biogeme.expressions import Beta
from biogeme import models
from biogeme.models import loglogit
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

print("Biogeme version:", importlib.metadata.version("biogeme"))
print(database)

# Define beta parameters
Constant1 = Beta('Constant1', 0, None, None, 1)
Constant2 = Beta('Constant2', 0, None, None, 0)
Constant3 = Beta('Constant3', 0, None, None, 0)
Duration = Beta('Duration', 0, None, None, 0)
Price = Beta('Price', 0, None, None, 0)

# Define utility functions
print(standard_duration)
Opt1 = Duration * standard_duration + Price * standard_price # De-facto askerlik 6 ay
Opt2 = Constant2 + Duration * paid1_duration + Price * paid1_price # 1. Seçenek bedelli askerlik
Opt3 = Constant3 + Duration * paid2_duration + Price * paid2_price # 2. Seçenek bedelli askerlik

# Utility dictionary
V = {1: Opt1, 2: Opt2, 3: Opt3}

# Availability - all alternatives are always available
av = {1: 1, 2: 1, 3: 1}

# Create the logit probability - USE
logprob = models.loglogit(V, av, chosen_alternative)

# Create BIOGEME object
biogeme = bio.BIOGEME(database, logprob)
biogeme.model_name = 'logit_military_generic'

# Calculate null loglikelihood
biogeme.calculate_null_loglikelihood(av)




results = biogeme.estimate()
print(results.short_summary())
print("LOGIT ESTIMATION RESULTS")
print(results.get_estimated_parameters())

pandasResults = results.get_estimated_parameters()
#pandasResults =  get_pandas_estimated_parameters(estimation_results=results)



# Willingness to pay
if {'Duration', 'Price'}.issubset(pandasResults['Name'].values):
    duration_coef = pandasResults.loc[pandasResults['Name'] == 'Duration', 'Value'].values[0]
    price_coef = pandasResults.loc[pandasResults['Name'] == 'Price', 'Value'].values[0]

    if price_coef != 0:
        wtp_per_week = -duration_coef / price_coef
        print(f"WTP for reducing service by 1 week: {wtp_per_week:,.0f} TL")
        print(f"WTP for reducing service by 6 week: {6 * wtp_per_week:,.0f} TL")
        print(f"WTP for reducing service by 12 week: {12 * wtp_per_week:,.0f} TL")

pandasResults.to_csv("logit_results.csv", index=False)

print("\nModel estimation complete")

print("Available attributes in raw_estimation_results:")
print([a for a in dir(results.raw_estimation_results) if not a.startswith("_")])
print(f"Log likelihood: {results.final_log_likelihood:.3f}")
print(f"Null log likelihood: {results.null_log_likelihood:.3f}")
