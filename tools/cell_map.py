"""Single source of truth for RIM-2013b workbook addresses.

Every ``Sheet!Cell`` reference used by the tooling lives here so that a workbook
version change is a one-file edit.

The workbook is a 10-column vectorisation: one spreadsheet column per simulation
year. See ``.claude/memory/workbook-column-layout.md``.
"""
from __future__ import annotations

WORKBOOK_GLOB = "Ryegrass-RIM-*-DOWNLOAD-NOW.xlsm"
WORKBOOK_VERSION = "RIM-2013b"

N_YEARS = 10

# --- Sheet names, exactly as they appear in the workbook -------------------
SHEET_STRATEGY = "2.Strategy"
SHEET_PROFILE = "1.Profile"
SHEET_PRICES = "+Prices"
SHEET_OPTIONS = "+Options"
SHEET_CALCS = "Calcs"
SHEET_BIO = "Bio results"
SHEET_ECO = "Eco results"

# --- Year -> column index --------------------------------------------------
# Year 1 is column D (4) on 2.Strategy / Bio results, column E (5) on
# Eco results, column C (3) on Calcs.
FIRST_COL_STRATEGY = 4   # D
FIRST_COL_BIO = 4        # D
FIRST_COL_ECO = 5        # E
FIRST_COL_CALCS = 3      # C


def year_col(year: int, first_col: int) -> int:
    """Return the 1-based column index for ``year`` (1..10)."""
    if not 1 <= year <= N_YEARS:
        raise ValueError(f"year must be 1..{N_YEARS}, got {year}")
    return first_col + year - 1


# --- Strategy input grid: named range Strategy_X = 2.Strategy!D4:M19 -------
# Row -> the decision it holds. Labels are the workbook's own row captions
# from column C.
STRATEGY_ROWS: dict[str, int] = {
    "enterprise": 4,               # "and control options:"  -> Wheat/Barley/...
    "time_of_sowing": 5,
    "soil_preparation": 6,
    "knock_down": 7,               # Knock-down / Double-knock
    "pre_emergent": 8,
    "establishment_system": 9,
    "crop_seeding_rate": 10,
    "post_emergent_1": 11,
    "post_emergent_2": 12,
    "post_emergent_3": 13,
    "grazing_intensity": 14,
    "spring_option": 15,
    "spring_swathe": 16,           # "          - Swathe"
    "spring_others": 17,           # "          - Others"
    "harvest_crops": 18,
    "harvest_others": 19,
}
STRATEGY_FIRST_ROW = 4
STRATEGY_LAST_ROW = 19

# Derived flags the Calcs block reads back off the strategy sheet
# (Calcs!C1 reads D64; Calcs!C7:C9 read D65; Calcs!C10:C14 read D66).
STRATEGY_FLAG_ROWS = (64, 65, 66)

# --- Output blocks ---------------------------------------------------------
# TabSum = Bio results!C2:M20 -- the full within-season state, per year.
# Column C holds the stage caption; columns D..M hold years 1..10.
TABSUM_PLANT_STAGES: dict[str, int] = {
    "first_chance_to_seed": 3,
    "ten_days_after_break": 4,
    "twenty_days_after_break": 5,
    "post_emergence_spray_time": 6,
    "early_spring": 7,
    "mature_setting_seed": 8,
}

TABSUM_SEED_STAGES: dict[str, int] = {
    "end_of_summer": 11,
    "after_first_chance_to_seed": 12,
    "seeds_ten_days_after_break": 13,
    "seeds_twenty_days_after_break": 14,
    "seeds_post_emergence_spray_time": 15,
    "seeds_spring": 16,
    "seed_produced_per_plant": 17,
    "seed_produced_per_m2": 18,
    "just_before_harvest": 19,
    "seeds_next_autumn": 20,
}

# EcoSum = Eco results!P5:AB17. Within that block, column P holds the caption
# and columns Q..Z hold years 1..10 -- i.e. the block's own layout, not the
# Eco results per-year columns E..N.
ECOSUM_ANCHOR_ROW = 5
ECOSUM_CAPTION_COL = 16   # P
ECOSUM_FIRST_YEAR_COL = 17  # Q
ECOSUM_TOTAL_COL = 28     # AB

ECOSUM_ROWS: dict[str, int] = {
    "income_crops": 7,
    "income_sheep": 8,
    "income_fodder": 9,
    "cost_competition": 10,
    "cost_herbicides": 11,
    "cost_mechanical": 12,
    "cost_user_options": 13,
    "cost_non_weed_grain": 14,
    "cost_non_weed_pasture": 15,
    "gross_margin": 16,
}
# Eco results!P5 holds the average gross margin across the 10 years.
ECOSUM_AVERAGE_GM = ("Eco results", 5, 16)

# --- Named ranges ----------------------------------------------------------
NAMED_RANGES = {
    "Strategy_X": "2.Strategy!D4:M19",
    "EcoSum": "Eco results!P5:AB17",
    "PopSum": "Bio results!O2:R87",
    "TabSum": "Bio results!C2:M20",
    "EcoA": "Eco results!P23:AB35",
    "EcoB": "Eco results!P41:AB53",
    "PopA": "Bio results!S2:V87",
    "PopB": "Bio results!W2:Z87",
    "TabA": "Bio results!C90:M108",
    "TabB": "Bio results!C111:M129",
    "Profile_Xa": "1.Profile!B5:Q27",
    "Profile_Xb": "1.Profile!C28:J36",
}

# --- Crop coding: Calcs!E184 ----------------------------------------------
CROP_CODE: dict[str, int] = {
    "Wheat": 0,
    "Barley": 1,
    "Canola": 2,
    "Legume": 3,
    "Volunt.": 4,
    "Clover": 5,
    "Cadiz": 6,
}

# +Options per-crop parameter columns (AG/AH/AI/AJ), keyed by crop code.
OPTIONS_CROP_COL: dict[int, int] = {0: 33, 1: 34, 2: 35, 3: 36}  # AG AH AI AJ
