import pandas as pd

# Set option to avoid future warnings
pd.set_option('future.no_silent_downcasting', True)

df = pd.read_csv("data_corrected.csv", skiprows=1)
df = df.drop(index=0).reset_index(drop=True)
df_dummy = pd.concat([df["Response ID"], df.iloc[:, 18:]], axis=1)

my_dict = {
    "Response ID": "ID",
    "Yaşınız": "age",
    "Eğitim Seviyeniz": "educ",
    "Çalışma Durumunuz - Selected Choice": "emp",
    "Çalışma Durumunuz - Diğer - Text": "emp_other",
    "Hane Gelir Seviyeniz Nedir?": "hh_inc",
    "Bireysel Gelir Seviyeniz Nedir?": "inc",
    "Hanenizde Kaç Kişi Yaşamakta?": "hh_size",
    "Hanenizde Kaç Kişinin Geliri Var?": "hh_emp",
    "Medeni Haliniz": "mrts",
    "1111 Sayılı Askerlik Kanunu Kapsamınca Zorunlu Askerlik Hizmetini Gerçekleştirmekle Yükümlü Müsünüz?": "mil_resp",
    "Zorunlu Askerlik Hizmetinizi Gerçekleştirdiniz mi?": "mil_done",
    "Zorunlu Askerlik Hizmetini Ne zaman Gerçekleştirdiniz?": "mil_time",
    "Zorunlu Askerlik Hizmetini Nasıl Gerçekleştirdiniz?": "mil_choice",
    "Şu Anki Askerlik Durumunuz Nedir?": "mil_curr",
}

df_dummy = df_dummy.rename(columns=my_dict)

# Rename patriotism question columns
cols = df_dummy.columns[25:45]
new_names = [f'patriotism {i + 1}' for i in range(len(cols))]
df_dummy = df_dummy.rename(columns=dict(zip(cols, new_names)))

# Rename secularism question columns
cols = df_dummy.columns[45:70]
new_names = [f'secularism {i + 1}' for i in range(len(cols))]
df_dummy = df_dummy.rename(columns=dict(zip(cols, new_names)))

# Rename choice block columns
cols = df_dummy.columns[15:25]
# Changed i to i + 1 to match the 1-10 range used in the loop later
new_names = [f'block_{i + 1}_choice' for i in range(len(cols))]
df_dummy = df_dummy.rename(columns=dict(zip(cols, new_names)))

# Map Likert scale values
my_dict = {
    "Hiç Uygun Değil": 1,
    "Hiç Uygun Değil 1": 1,
    "Uygun Değil": 2,
    "Uygun Değil 2": 2,
    "Biraz Uygun": 3,
    "Uygun": 4,
    "Çok Uygun": 5
}

cols = df_dummy.columns[25:70]
df_dummy.loc[:, cols] = df_dummy.loc[:, cols].replace(my_dict).infer_objects(copy=False)

df = df_dummy.copy()

# Static columns (personal characteristics + indicator questions)
static_cols = list(df.columns[:15]) + list(df.columns[25:70])

# Block template
block_template = [
    "scenario_id",
    "standard_price",
    "standard",
    "paid1_duration",
    "paid1_price",
    "paid2_duration",
    "paid2_price",
    "choice"
]

# Process each block
frames = []
for i in range(1, 11):
    prefix = f"block_{i}_"
    current_block_cols = [f"{prefix}{col}" for col in block_template]
    available_cols = [c for c in current_block_cols if c in df.columns]

    if not available_cols:
        continue

    existing_static = [c for c in static_cols if c in df.columns]
    subset = df[existing_static + available_cols].copy()
    rename_map = {col: col.replace(prefix, '') for col in available_cols}
    subset.rename(columns=rename_map, inplace=True)

    subset['choice_number'] = i
    frames.append(subset)

long_df = pd.concat(frames, ignore_index=True)

# Reorder columns
cols = list(long_df.columns)
cols.insert(0, cols.pop(cols.index('choice_number')))
long_df = long_df[cols]

# Rename and reorder columns
long_df.rename(columns={"standard": "standard_duration"}, inplace=True)
cols = list(long_df.columns)
i, j = cols.index('standard_duration'), cols.index('standard_price')
cols[i], cols[j] = cols[j], cols[i]

i, j = cols.index('ID'), cols.index('choice_number')
cols[i], cols[j] = cols[j], cols[i]
long_df = long_df[cols]

# Map choice values - use non-inplace method
choice_dict = {
    "Seçenek A": "A",
    "Seçenek B": "B",
    "Seçenek C": "C",
}
long_df["choice"] = long_df["choice"].replace(choice_dict)

# Create dummy variables - make sure all choice options exist
dummies = pd.get_dummies(long_df['choice'], prefix='choice', prefix_sep='_', drop_first=False)

# Check if we have all expected choice columns
# In your data, sometimes there is no "C" choice
# So we need to add missing columns with zeros
expected_choice_columns = ['choice_A', 'choice_B', 'choice_C']
for col in expected_choice_columns:
    if col not in dummies.columns:
        dummies[col] = 0

# Reorder columns to keep consistent order
dummies = dummies[expected_choice_columns]

# Merge and remove unnecessary columns
long_df = pd.concat([long_df, dummies], axis=1)
long_df.drop(columns=['choice', "scenario_id"], inplace=True)

# Define categorical mappings
age_list = ["18-20", "20-24", "25-29", "29-34", "34-39"]
educ_list = ["İlkokul", "Lise", "M.Y Okulu", "Üniversite", "Yüksek Lisans", "Doktora"]
emp_list = ["Tam Zamanlı", "Yarı Zamanlı(Part-Time)", "İşsiz fakat iş arıyor", "İşsiz", "Öğrenci", "Diğer"]
hh_inc_list = [
    "0 - 25.000₺", "25.001₺ - 45.000₺", "45.001₺ - 70.000₺",
    "70.001₺ - 95.000₺", "95.001₺ - 120.000₺", "120.001₺ - 145.000₺",
    "145.001₺ - 190.000₺", "190.000₺ ve Üzeri"
]
inc_list = [
    "0 - 10.000₺", "10.001₺ - 20.000₺", "20.001₺ - 30.000₺",
    "30.001₺ - 40.000₺", "40.001₺ - 50.000₺", "50.001₺ - 60.000₺",
    "60.001₺ - 70.000₺", "70001₺ ve Üzeri"
]
hh_size_list = ["1", "2", "3", "4", "5 ve Üzeri"]
hh_emp_list = ["1", "2", "3", "4", "5 ve Üzeri"]
mrts_list = ["Bekar", "Evli", "Boşanmış"]
mil_resp_list = ["Hayır", "Evet"]
mil_done_list = ["Hayır", "Evet"]
mil_choice_list = ["Uzun Dönem(12 ay) Askerlik", "Kısa Dönem(6 ay) Askerlik", "Bedelli Askerlik"]
mil_curr_list = ["Daha Çağrılmadım.", "Tecilliyim.(Eğitim durumu vb.)"]

# Define mappings
mapping_defs = {
    'age': age_list,
    'educ': educ_list,
    'emp': emp_list,
    'hh_inc': hh_inc_list,
    'inc': inc_list,
    'hh_size': hh_size_list,
    'hh_emp': hh_emp_list,
    'mrts': mrts_list,
    'mil_resp': mil_resp_list,
    'mil_done': mil_done_list,
    'mil_choice': mil_choice_list,
    'mil_curr': mil_curr_list,
}

# Check for unmapped values
for col, lst in mapping_defs.items():
    if col in long_df.columns:
        vals = long_df[col].dropna().astype(str).str.strip().unique()
        missing = [v for v in vals if v not in lst and v != 'nan' and v != '']
        if missing:
            print(f"{col} — unmapped values: {missing}")

# Apply mappings
for col, lst in mapping_defs.items():
    if col in long_df.columns:
        map_dict = {v: i for i, v in enumerate(lst)}
        long_df[col] = long_df[col].astype(str).str.strip().map(map_dict).astype('Int64')

# Convert choice columns to integer type - FIXED: Use only columns that exist
choice_columns = ["choice_A", "choice_B", "choice_C"]
# Filter to only include columns that actually exist in the dataframe
existing_choice_columns = [col for col in choice_columns if col in long_df.columns]

if existing_choice_columns:
    long_df[existing_choice_columns] = long_df[existing_choice_columns].astype(int)

# Save processed data
long_df.to_csv("curated_data.csv", index=False)
print("Data preprocessing completed successfully!")
print(f"Processed {len(long_df)} rows")
print(f"Available choice columns: {existing_choice_columns}")