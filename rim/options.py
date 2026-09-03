from __future__ import annotations

from rim.herbicides import post_emergent_names, pre_emergent_names

CROP_OPTIONS = [
    "Wheat",
    "Barley",
    "Canola",
    "Legume crop",
    "Volunteer pasture",
    "Sub-Clover pasture",
    "Cadiz pasture",
]

SEEDING_TIMING_OPTIONS = ["Dry", "Wet", "Delayed (1-2 wks)", "+Delayed (3 wks)"]
SEEDING_TECHNIQUE_OPTIONS = ["No-till", "Full-cut (wide points)"]
SEEDING_RATE_OPTIONS = ["Standard", "High"]
PRE_TILLAGE_OPTIONS = ["None", "Tickle", "Mouldboard plough"]
KNOCKDOWN_OPTIONS = ["None", "Single knock-down", "Double knock-down"]
YES_NO_OPTIONS = ["No", "Yes"]

# The workbook names its herbicides and rates each one per crop; these come from
# Calcs rows 58-62 and 71-75 via data/calcs_survival_table.json. See
# rim/herbicides.py.
PRE_EMERGENT_OPTIONS = pre_emergent_names()
POST_EMERGENT_OPTIONS = post_emergent_names()
SPRING_OPTIONS = ["None", "Green manuring", "Brown manuring", "Mowing", "Hay & Silage", "Topping", "Swathing"]
GRAZING_OPTIONS = ["None", "Standard", "High"]
HARVEST_OPTIONS = [
    "Standard",
    "Whole paddock burn",
    "Narrow windrow burn",
    "Chaff-tramlining",
    "Chaff cart+dumps",
    "HSD",
    "BDS",
]
