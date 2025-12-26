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
database.dataframe['standard_price_sc'] = database.dataframe['standard_price'] / 100000.0
database.dataframe['paid1_price_sc']    = database.dataframe['paid1_price'] / 100000.0
database.dataframe['paid2_price_sc']    = database.dataframe['paid2_price'] / 100000.0

# Redefine the Biogeme variables to point to these SCALED columns
standard_price_sc = Variable('standard_price_sc')
paid1_price_sc    = Variable('paid1_price_sc')
paid2_price_sc    = Variable('paid2_price_sc')



# Patriotism = coef_educ_pat * educ + eta_pat
# Secularism = coef_educ_sec * educ + eta_sec

eta_pat = Draws("eta_pat", "NORMAL")
eta_sec = Draws("eta_sec", "NORMAL")

# coef_educ_pat = Beta("coef_educ_pat", 0, None, None, 0)
# coef_educ_sec = Beta("coef_educ_sec", 0, None, None, 0)

# No demographics
#Secular = alpha_sec + omega_sec
Patriotism = eta_pat
Secularism = eta_sec


ASC_Paid = Beta("ASC_Paid", 0.1, None, None, 0)
Beta_Time = Beta("Beta_Time", -0.5, None, None, 0)
Beta_Fee  = Beta("Beta_Fee", -0.5, None, None, 0)



Theta_Time_Pat = Beta("Theta_Time_Pat", 0, None, None, 0)
Theta_Time_Sec = Beta("Theta_Time_Sec", 0, None, None, 0)
Theta_Fee_Pat  = Beta("Theta_Fee_Pat", 0, None, None, 0)
Theta_Fee_Sec  = Beta("Theta_Fee_Sec", 0, None, None, 0)

Delta_Pat_Paid = Beta("Delta_Pat_Paid", 0, None, None, 0)
Delta_Sec_Paid = Beta("Delta_Sec_Paid", 0, None, None, 0)


Beta_Time_i = Beta_Time + Theta_Time_Pat * Patriotism + Theta_Time_Sec * Secularism
Beta_Fee_i  = Beta_Fee  + Theta_Fee_Pat * Patriotism  + Theta_Fee_Sec * Secularism

Beta_Time_Individual = (
    Beta_Time
    + Theta_Time_Pat * Patriotism
    + Theta_Time_Sec * Secularism
)

Beta_Fee_Individual = (
    Beta_Fee
    + Theta_Fee_Pat * Patriotism
    + Theta_Fee_Sec * Secularism
)

V1 = Beta_Time_i * standard_duration + Beta_Fee_i * standard_price_sc
V2 = ASC_Paid + Delta_Pat_Paid * Patriotism + Delta_Sec_Paid * Secularism + \
     Beta_Time_i * paid1_duration + Beta_Fee_i * paid1_price_sc
V3 = ASC_Paid + Delta_Pat_Paid * Patriotism + Delta_Sec_Paid * Secularism + \
     Beta_Time_i * paid2_duration + Beta_Fee_i * paid2_price_sc


# Constant2 = Beta("Constant2", 0, None, None, 0)
# Constant3 = Beta("Constant3", 0, None, None, 0)
#
# Duration = Beta("Duration", 0, None, None, 0)
# Price = Beta("Price", 0, None, None, 0)
#
# lambda_sec = Beta("lambda_sec", 0, None, None, 0)

# V1 = Duration * standard_duration + Price * standard_price
#
# V2 = (
#     Constant2
#     + Duration * paid1_duration
#     + Price * paid1_price
#     + lambda_sec * Secular
# )
#
# V3 = (
#     Constant3
#     + Duration * paid2_duration
#     + Price * paid2_price
#     + lambda_sec * Secular
# )

V = {1: V1, 2: V2, 3: V3}
av = {1: 1, 2: 1, 3: 1}




meas_pat = Variable("patriotism 1")
Lam_Pat = Beta("Lam_Pat", 1, None, None, 0)

mu_p1 = Beta("mu_p1", -1.0, None, None, 0)
d_p2  = Beta("d_p2", 0.8, 0.001, None, 0) # Start at 0.8, Min 0.001
d_p3  = Beta("d_p3", 0.8, 0.001, None, 0)
d_p4  = Beta("d_p4", 0.8, 0.001, None, 0)

tau_p1 = mu_p1
tau_p2 = tau_p1 + d_p2
tau_p3 = tau_p2 + d_p3
tau_p4 = tau_p3 + d_p4

P_star = Lam_Pat * Patriotism
prob_meas_pat = (
    (meas_pat == 1) * NormalCdf(tau_p1 - P_star) +
    (meas_pat == 2) * (NormalCdf(tau_p2 - P_star) - NormalCdf(tau_p1 - P_star)) +
    (meas_pat == 3) * (NormalCdf(tau_p3 - P_star) - NormalCdf(tau_p2 - P_star)) +
    (meas_pat == 4) * (NormalCdf(tau_p4 - P_star) - NormalCdf(tau_p3 - P_star)) +
    (meas_pat == 5) * (1 - NormalCdf(tau_p4 - P_star))
)


meas_sec = Variable("secularism 1")
Lam_Sec = Beta("Lam_Sec", 1, None, None, 0)

mu_s1 = Beta("mu_s1", -1.0, None, None, 0)
d_s2  = Beta("d_s2", 0.8, 0.001, None, 0)
d_s3  = Beta("d_s3", 0.8, 0.001, None, 0)
d_s4  = Beta("d_s4", 0.8, 0.001, None, 0)

tau_s1 = mu_s1
tau_s2 = tau_s1 + d_s2
tau_s3 = tau_s2 + d_s3
tau_s4 = tau_s3 + d_s4

S_star = Lam_Sec * Secularism
prob_meas_sec = (
    (meas_sec == 1) * NormalCdf(tau_s1 - S_star) +
    (meas_sec == 2) * (NormalCdf(tau_s2 - S_star) - NormalCdf(tau_s1 - S_star)) +
    (meas_sec == 3) * (NormalCdf(tau_s3 - S_star) - NormalCdf(tau_s2 - S_star)) +
    (meas_sec == 4) * (NormalCdf(tau_s4 - S_star) - NormalCdf(tau_s3 - S_star)) +
    (meas_sec == 5) * (1 - NormalCdf(tau_s4 - S_star))
)


prob_choice = models.loglogit(V, av, chosen_alternative)

joint_prob = prob_choice * prob_meas_pat * prob_meas_sec

simulated_prob = MonteCarlo(joint_prob)

log_likelihood = log(simulated_prob + 1e-300)



# ==============================================================================
# ESTIMATION
# ==============================================================================
biogeme = bio.BIOGEME(database, log_likelihood)
biogeme.model_name = "HCM_minimal_secular"
biogeme.numberOfDraws = 200


results = biogeme.estimate ()
print(results.short_summary())
