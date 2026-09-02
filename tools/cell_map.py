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

# +Options per-crop parameter columns: AG=Wheat, AH=Barley, AI=Canola, AJ=Legume.
OPTIONS_WHEAT_COL = 33   # AG
OPTIONS_BARLEY_COL = 34  # AH
OPTIONS_CANOLA_COL = 35  # AI
OPTIONS_LEGUME_COL = 36  # AJ

# --- Stage multipliers: Calcs!C99 and C164:C170 ----------------------------
# Combine the survival factors into the seven per-stage multipliers that
# Bio results!D3:D20 applies. C99 (normal-harvest seed removal) folds into C170.
MULTIPLIER_ROWS = (99, 164, 165, 166, 167, 168, 169, 170)
# Calcs!P35:P39 -- how many of the three post-emergent slots hold each product.
POST_EM_USE_COUNT_ROWS = (35, 36, 37, 38, 39)
POST_EM_USE_COUNT_COL = 16  # P

# --- Table 8: Calcs!C193:M291, keyed by the rotation key (Calcs row 189) ----
TABLE8_FIRST_ROW = 193
TABLE8_LAST_ROW = 291
TABLE8_KEY_COL = 3  # C

# --- Germination: +Options -------------------------------------------------
# Five cohorts germinate through the season. Regenerating pasture uses rows
# 105-109 (AG = no tickle, AI = tickled); a sown paddock uses rows 115-119
# across all four tickle x establishment combinations.
GERMINATION_COHORTS = 5
GERMINATION_PASTURE_ROW = 105
GERMINATION_SOWN_ROW = 115

# --- Cost table: Calcs C105:C147 <- N105:T147 ------------------------------
# The cost twin of the survival block: same option order, paired at r + 50.
# Unlike the survival block it is written as nested IFs rather than HLOOKUP,
# and the crop-code -> column mapping is NOT uniform across the rows, so the
# extractor derives it per row from the formulas. See COST_ROW_OFFSET.
COST_TABLE_RANGE = "Calcs!N105:T147"
COST_FIRST_ROW = 105
COST_LAST_ROW = 147
COST_ROW_OFFSET = 50  # survival row r has its cost twin at r + 50

# --- Economics inputs (block 7) --------------------------------------------
NON_WEED_COST_ROWS = {"legumes": 299, "wheat": 300, "barley": 301, "canola": 302}
PASTURE_COST_ROW = 306
MACHINERY_REPAYMENT_ROW = 358
TREND_ROWS = {
    "crop_yield_trend": 362,
    "pasture_productivity_trend": 363,
    "crop_price_inflation": 364,
    "sheep_price_inflation": 365,
    "input_cost_inflation": 366,
}
# +Prices!AV68:AV72 -- the annual rates the Calcs 362-366 factors compound from.
TREND_RATE_CELLS = {
    "crop_yield_trend": "AV68",
    "pasture_productivity_trend": "AV69",
    "crop_price_inflation": "AV70",
    "sheep_price_inflation": "AV71",
    "input_cost_inflation": "AV72",
}
# '+Prices'!AR72:AR77 -- per-hectare repayment per HWSC machine, in the order
# Calcs!C352:C357 counts their ages. O37 is the loan term in years.
MACHINERY_REPAYMENT_CELLS = {
    "cart_and_burn": "AR72",
    "narrow_windrow": "AR73",
    "harrington_seed_destructor": "AR74",
    "chaff_tramlining": "AR75",
    "spare_slot": "AR76",
    "bale_direct": "AR77",
}
MACHINERY_LOAN_TERM_CELL = "O37"
INTEREST_CELL = ("+Prices", 73, 48)  # AV73
TAX_CELL = ("+Prices", 74, 48)       # AV74

# --- Yield inputs (block 6), +Options per-crop rows -------------------------
YIELD_PARAM_ROWS = {
    "weed_free_yield": 56,
    "plant_density_standard": 59,
    "plant_density_high": 60,
    "harvest_index": 61,             # Bio results D46:D54, hay and baling
    "fodder_conversion": 62,
    "benefit_early_sowing": 67,      # Bio results D28
    "benefit_after_green_manure": 68,   # D29 term 1
    "benefit_after_brown_manure": 69,   # D29 term 2
    "benefit_after_mowing": 70,         # D29 term 3
    "penalty_not_swathing": 73,      # D25
    "penalty_crop_topping": 74,      # D26
    "legume_after_legume_penalty": 77,
    "penalty_sowing_delayed": 79,    # D24, delayed 1-2 weeks
    "penalty_sowing_plus_delayed": 80,  # D24, +delayed
    "phytotoxicity_per_spray": 81,   # D23, x Calcs!P40
    "max_yield_loss": 86,
    "competition_a": 88,
    "competition_b": 89,
}
MOULDBOARD_YIELD_BENEFIT_CELL = ("+Options", 25, 8)  # H25, Bio results D27
RYEGRASS_COMPETITIVENESS_ROWS = (136, 137, 138, 139)  # AG only, per crop code 0-3

# --- Yield block: Bio results!D23:D54 (block 6) -----------------------------
YIELD_ROWS = tuple(range(23, 55))
# --- Economics block: Eco results!E3:E63 (block 7) --------------------------
# Captured as a whole so a fixture can check receipts, costs and gross margin
# line by line rather than only the EcoSum summary.
ECO_DETAIL_ROWS = tuple(range(3, 64))

# --- Block 7 price inputs (+Prices and 1.Profile) ---------------------------
# Non-weed-control cost per crop, Calcs!C299:C302 -> +Prices row 96.
NON_WEED_CROP_COST = {"3": "AM96", "0": "AJ96", "1": "AK96", "2": "AL96"}
# Fertiliser saved when the crop was green-manured, Calcs!C299:C302.
GREEN_MANURE_SAVING = {"cereal": "F19", "canola": "G19", "legume": "H19"}
CULTIVATION_ENV_COST = "AC113"          # on Calcs, NOT +Prices. Calcs!C298, halved per trigger.
# Pasture non-weed costs by rotation key, Calcs!C303:C305.
PASTURE_COST_VOLUNTEER = {"4": "AJ111", "5": "AK111", "6": "AL111"}
PASTURE_COST_CLOVER = {"7_resown": "AJ123", "7": "AJ119", "8": "AK119", "9": "AL119"}
PASTURE_COST_CADIZ = {"10": "AJ129", "11": "AK129", "12": "AL129"}
# 1.Profile row 8: grain prices D:G, fodder K:M, sheep gross margin P.
PROFILE_PRICE_CELLS = {
    "grain_0": "D8", "grain_1": "E8", "grain_2": "F8", "grain_3": "G8",
    "hay": "K8", "silage": "L8", "bales": "M8", "sheep_gm_per_dse": "P8",
}
