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

# --- Rotation coding cascade: Calcs rows 184-189 ---------------------------
# Five stacked rows turn the enterprise labels into the VLOOKUP key that
# Table 8 (Calcs!C193:M291) is indexed by. Columns run C, D = paddock history
# (2 years ago, 1 year ago), then E..N = simulation years 1..10 -- note this is
# two columns further right than the other Calcs blocks.
FIRST_COL_ROTATION = 5  # E
ROTATION_HISTORY_COLS = {"two_years_ago": 3, "one_year_ago": 4}  # C, D

ROTATION_ROWS: dict[str, int] = {
    "crop_code": 184,          # enterprise label -> 0..6
    "phase_code": 185,         # pasture phase year within a run
    "pasture_carry": 186,      # carries a finished pasture phase forward
    "barley_code": 187,        # barley-specific offset
    "break_since_canola": 188, # years since the last canola
    "rotation_key": 189,       # the Table 8 VLOOKUP key
}

# Paddock history: the enterprise grown before the simulation starts, as
# single letters (w/b/c/l/v/s/z). Literal input cells, no formula.
HISTORY_CELLS = {"one_year_ago": ("Calcs", 181, 14), "two_years_ago": ("Calcs", 182, 14)}

# Table 8: enterprise code -> weed-free yield, ryegrass control, stocking rates.
TABLE8_RANGE = "Calcs!C193:M291"

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

# Calcs!C184/D184 code the paddock history from single letters rather than the
# full enterprise names used for the simulation years.
HISTORY_CODE: dict[str, int] = {
    "w": 0, "b": 1, "c": 2, "l": 3, "v": 4, "s": 5, "z": 6,
}

# --- Survival factor block: Calcs C55:C97 <- N54:T97 -----------------------
# Row 54 is the crop-code header (0..6 across columns N..T). Rows 55-97 are the
# control options; column A holds the HLOOKUP offset (always row - 54) and
# column B the label. The table value is the *control* fraction; the workbook
# stores 1 - value as the survival factor.
SURVIVAL_TABLE_RANGE = "Calcs!N54:T97"
SURVIVAL_HEADER_ROW = 54
SURVIVAL_FIRST_ROW = 55
SURVIVAL_LAST_ROW = 97
SURVIVAL_CROP_COLS = tuple(range(14, 21))  # N..T = crop codes 0..6

# Rows 68-70 (seeding timing) are not crop-indexed. Header row 67 labels
# column P "No-till" and column Q "Full cut".
SURVIVAL_NO_TILL_COL = 16   # P
SURVIVAL_FULL_CUT_COL = 17  # Q
SURVIVAL_SEEDING_ROWS = (68, 69, 70)

# Which activation cell (Calcs C7:C49) feeds which survival factor row.
# Deliberately explicit: the mapping is not a uniform offset -- note 78 <- 31
# and 79 <- 30 are transposed relative to their neighbours.
SURVIVAL_SOURCE: dict[int, int] = {
    55: 7, 56: 8, 57: 9,                      # knock-down / double-knock
    58: 10, 59: 11, 60: 12, 61: 13, 62: 14,   # pre-emergent
    65: 17,                                   # mouldboard plough
    69: 21, 70: 22,                           # seeding timing (see SURVIVAL_SEEDING_ROWS)
    71: 23, 72: 24, 73: 25, 74: 26, 75: 27,   # post-emergent
    78: 31, 79: 30, 80: 32, 81: 33, 82: 34,   # spring options
    83: 35, 84: 36, 85: 37, 86: 38,
    87: 39, 88: 40,                           # swathing
    89: 41, 90: 42, 91: 43, 92: 44, 93: 45,   # harvest
    94: 46, 95: 47, 96: 48, 97: 49,
}
# Calcs!C68 is the one row fed by two activation cells: C19 or C20.
SURVIVAL_ROW_68_SOURCES = (19, 20)

# The full activation block, captured so the survival port can be tested with
# Excel's own inputs before Calcs!C7:C27 itself is ported (block 2).
ACTIVATION_ROWS = tuple(range(7, 50))
SURVIVAL_ROWS = tuple(sorted(set(SURVIVAL_SOURCE) | {68}))
