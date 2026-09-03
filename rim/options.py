from __future__ import annotations

from rim.control_options import names as _names

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
YES_NO_OPTIONS = ["No", "Yes"]

# Every weed-control decision comes from the workbook's own option list, with
# its control and its cost -- Calcs rows 55-97 and 105-147. See
# rim/control_options.py; nothing below is typed.
KNOCKDOWN_OPTIONS = _names("knockdown")
PRE_EMERGENT_OPTIONS = _names("pre_emergent")
POST_EMERGENT_OPTIONS = _names("post_emergent_1")
SPRING_OPTIONS = _names("spring_option")
SPRING_SWATHE_OPTIONS = _names("spring_swathe")
SPRING_OTHERS_OPTIONS = _names("spring_others")
HARVEST_OPTIONS = _names("harvest_option")
HARVEST_OTHERS_OPTIONS = _names("harvest_others")
GRAZING_OPTIONS = ["None", "Standard", "High"]
