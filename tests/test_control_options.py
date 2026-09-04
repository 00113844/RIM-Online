"""Every weed-control decision, rated and priced by the workbook.

``Calcs`` rows 55-97 and 105-147 are the same option list twice -- what each
does to ryegrass, and what it costs -- paired at ``r + 50``, both indexed by
crop. The app used to carry invented numbers for most of it: a knock-down was
"single" or "double" at 0.55 / 0.75, spring and harvest were priced from a
hand-written table, and three of RIM's decisions did not exist at all.

Each rule here re-reads the generated file it depends on, so a rule cannot
outlive its evidence.
"""
from __future__ import annotations

import json

import pytest

from rim import control_options as co
from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PRICES, build_default_strategy
from rim.economics import compute_costs
from rim.herbicides import upgrade_row
from rim.ryegrass import total_control_fraction
from utils.applicability import neutralise, product_options

WHEAT, BARLEY, CANOLA, LEGUME, VOLUNTEER, CLOVER, CADIZ = range(7)


@pytest.fixture(scope="module")
def tables() -> tuple[dict, dict]:
    with open(co.SURVIVAL_PATH, encoding="utf-8") as handle:
        survival = json.load(handle)["options"]
    with open(co.COST_PATH, encoding="utf-8") as handle:
        costs = json.load(handle)["options"]
    return survival, costs


# -- Every option is read, not typed ------------------------------------------


def test_each_option_matches_the_generated_tables(tables) -> None:
    survival, costs = tables
    for field in co.FIELDS:
        for option in co.options_for(field):
            entry = survival[str(option.row)]
            assert option.workbook_label == entry["label"]
            assert option.control == {
                int(c): float(v) for c, v in entry["by_crop_code"].items()
            }
            cost_row = costs.get(str(option.row + co.COST_ROW_OFFSET), {})
            assert option.cost == {
                int(c): float(v)
                for c, v in cost_row.get("cost_by_crop_code", {}).items()
            }


def test_the_cost_row_sits_fifty_below_its_control_row(tables) -> None:
    """The pairing the whole table depends on."""
    _, costs = tables
    for field in co.FIELDS:
        for option in co.options_for(field):
            entry = costs.get(str(option.row + co.COST_ROW_OFFSET))
            if entry is not None:
                assert entry["survival_row"] == option.row


def test_the_column_swap_is_resolved_before_it_reaches_here(tables) -> None:
    """Rows use one of two crop-column orders; both must already be decoded.

    Reading the block with a single mapping mis-costs every spring and harvest
    option on clover and Cadiz. The generated file records each row's own
    signature, so a row carrying the swapped one must still price Clover and
    Cadiz from the right cells.
    """
    _, costs = tables
    swapped = [entry for entry in costs.values()
               if entry.get("column_signature") == "NOPQRTS"]

    assert swapped, "no row carries the swapped signature - has the table changed?"
    for entry in swapped:
        assert set(entry["cost_by_crop_code"]) == {str(i) for i in range(7)}


def test_every_decision_the_registry_owns_is_on_the_strategy_sheet() -> None:
    assert set(co.FIELDS) == set(co.FIELD_ROWS)
    assert co.INERT["harvest_option"] == co.STANDARD_HARVEST
    assert all(co.INERT[f] == co.NONE for f in co.FIELDS if f != "harvest_option")


# -- Knock-downs are products, not a count of passes --------------------------


def test_the_knockdown_offers_the_workbooks_three_products() -> None:
    assert co.names("knockdown") == [
        "None", "Glyphosate", "Paraquat", "Double knock-down",
    ]


def test_the_double_knock_controls_more_than_either_single(tables) -> None:
    survival, _ = tables
    single = co.control("knockdown", "Glyphosate", WHEAT)
    double = co.control("knockdown", "Double knock-down", WHEAT)

    assert double > single
    assert single == float(survival["55"]["by_crop_code"]["0"])
    assert double == float(survival["57"]["by_crop_code"]["0"])


def test_the_double_knock_costs_more_than_either_single() -> None:
    assert (co.cost("knockdown", "Double knock-down", WHEAT)
            > co.cost("knockdown", "Glyphosate", WHEAT)
            > co.cost("knockdown", "Paraquat", WHEAT))


def test_a_knockdown_costs_less_on_pasture_than_in_a_crop() -> None:
    """Calcs row 105: $26/ha in a crop, $22/ha in a pasture."""
    assert co.cost("knockdown", "Glyphosate", VOLUNTEER) < \
           co.cost("knockdown", "Glyphosate", WHEAT)


# -- The three decisions the app used to lack ---------------------------------


@pytest.mark.parametrize("field, expected", [
    ("spring_swathe", ["None", "Swathe only", "Swathe + spray"]),
    ("spring_others", ["None", "Custom spring option 1", "Custom spring option 2"]),
    ("harvest_others", ["None", "Whole paddock burn",
                        "Custom harvest option 1", "Custom harvest option 2"]),
])
def test_the_missing_columns_exist_and_offer_the_workbooks_options(field, expected) -> None:
    assert co.names(field) == expected


def test_swathing_does_nothing_on_pasture() -> None:
    """Calcs rows 87-88 are zero for crop codes 4-6: there is nothing to swathe."""
    for code in (VOLUNTEER, CLOVER, CADIZ):
        assert not co.works_on("spring_swathe", "Swathe only", code)
    assert product_options("spring_swathe", "Volunteer pasture") == ["None"]


def test_spraying_the_swathe_controls_more_than_not() -> None:
    assert co.control("spring_swathe", "Swathe + spray", WHEAT) > \
           co.control("spring_swathe", "Swathe only", WHEAT)
    assert co.cost("spring_swathe", "Swathe + spray", WHEAT) > \
           co.cost("spring_swathe", "Swathe only", WHEAT)


def test_burning_everything_works_on_pasture_where_a_header_does_not() -> None:
    """Whole-paddock burning is on the others row because it needs no header."""
    assert co.works_on("harvest_others", "Whole paddock burn", VOLUNTEER)
    assert product_options("harvest_option", "Volunteer pasture") == ["Standard"]
    assert "Whole paddock burn" in product_options("harvest_others", "Volunteer pasture")


def _row(**decisions) -> dict:
    return upgrade_row({**build_default_strategy(1)[0], "crop": "Wheat",
                        "pre_emergent": "None", "post_emergent_1": "None",
                        **decisions})


def test_the_new_columns_reach_the_engine() -> None:
    def control(**decisions) -> float:
        return total_control_fraction(_row(**decisions), DEFAULT_OPTIONS, None)

    assert control(spring_swathe="Swathe + spray") > control()
    assert control(spring_others="Custom spring option 1") > control()
    assert control(harvest_others="Whole paddock burn") > control()


def test_the_new_columns_are_paid_for() -> None:
    def cost(**decisions) -> float:
        return compute_costs(_row(**decisions), DEFAULT_PRICES,
                             DEFAULT_OPTIONS, 0.0)["weed_control_cost"]

    assert cost(spring_swathe="Swathe + spray") == pytest.approx(
        cost() + co.cost("spring_swathe", "Swathe + spray", WHEAT))
    assert cost(harvest_others="Whole paddock burn") == pytest.approx(
        cost() + co.cost("harvest_others", "Whole paddock burn", WHEAT))


# -- Nothing invented is left in the defaults ---------------------------------


def test_the_defaults_no_longer_rate_or_price_weed_control() -> None:
    """Invented numbers here would silently disagree with the workbook."""
    assert set(DEFAULT_OPTIONS["control_effect"]) == {"pre_tillage"}, (
        "a control rate outside the workbook's table has come back"
    )
    assert "costs" not in DEFAULT_OPTIONS, (
        "a hand-written cost table has come back"
    )


def test_the_shipped_plan_is_priced_from_the_workbook() -> None:
    row = build_default_strategy(1)[0]
    expected = (co.cost("pre_emergent", row["pre_emergent"], WHEAT)
                + co.cost("post_emergent_1", row["post_emergent_1"], WHEAT))

    costs = compute_costs(row, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0)

    assert costs["herbicide_cost"] == pytest.approx(expected)


# -- Carrying version-1 and version-2 plans forward ---------------------------


@pytest.mark.parametrize("field, old, new", [
    # Version 1 counted knock-down passes; the workbook names products.
    ("knockdown", "Single knock-down", "Glyphosate"),
    ("knockdown", "DoubleK", "Double knock-down"),
    # Version 3 briefly used the workbook's own abbreviations.
    ("spring_option", "Green M.", "Green manuring"),
    ("spring_option", "Hay & Silage", "Hay + spray"),
    ("harvest_option", "Narr+B.", "Narrow windrow burn"),
    ("harvest_option", "BDS", "Bale Direct System"),
    ("harvest_option", "HSD", "Harrington Seed Destructor"),
    ("pre_emergent", "Triflur+Tria", "Trifluralin + triallate"),
])
def test_an_older_name_resolves_to_the_current_one(field, old, new) -> None:
    assert upgrade_row({"crop": "Wheat", field: old})[field] == new


def test_a_name_resolves_however_it_is_cased_or_spaced() -> None:
    """Hand-written scenario files should not fail on whitespace."""
    assert co.canonical("pre_emergent", "  sakura ") == "Sakura"
    assert co.canonical("harvest_option", "bale direct system") == "Bale Direct System"


def test_every_option_answers_to_the_workbooks_own_name() -> None:
    """The abbreviation stays a valid key, so nothing written against it breaks."""
    for field in co.FIELDS:
        for option in co.options_for(field):
            assert co.find(field, option.workbook_name) is option
            assert co.find(field, option.workbook_label) is option


def test_choices_that_were_in_the_wrong_column_move() -> None:
    """Swathing was a spring option; burning everything was a harvest control."""
    swathed = upgrade_row({"crop": "Wheat", "spring_option": "Swathing"})
    assert swathed["spring_option"] == co.NONE
    assert swathed["spring_swathe"] == "Swathe only"

    burnt = upgrade_row({"crop": "Wheat", "harvest_option": "Whole paddock burn"})
    assert burnt["harvest_option"] == co.STANDARD_HARVEST
    assert burnt["harvest_others"] == "Whole paddock burn"


def test_upgrading_fills_in_the_decisions_that_did_not_exist() -> None:
    upgraded = upgrade_row({"crop": "Wheat"})

    for field in co.FIELDS:
        assert upgraded[field] == co.INERT[field]


def test_upgrading_twice_changes_nothing_more() -> None:
    once = upgrade_row({"crop": "Canola", "knockdown": "Double knock-down",
                        "spring_option": "Swathing", "pre_emergent": "Yes"})

    assert upgrade_row(once) == once


def test_migrating_never_picks_a_product_the_crop_cannot_use() -> None:
    """The rule that resolves a version-1 "Yes" must respect the crop.

    Structural gates are a separate matter and still apply afterwards -- a
    volunteer pasture regenerates rather than being sown, so it has no seeding
    pass to carry the pre-emergent that the table does rate for it. What must
    never happen is migrating to a product the workbook rates at zero there.
    """
    from utils.applicability import product_mismatches

    for crop in ("Wheat", "Barley", "Canola", "Legume crop",
                 "Volunteer pasture", "Sub-Clover pasture", "Cadiz pasture"):
        row = upgrade_row({"crop": crop, "pre_emergent": "Yes",
                           "post_emergent": "Yes", "knockdown": "Single knock-down",
                           "seeding_timing": "Delayed (1-2 wks)"})

        assert product_mismatches([row]) == [{}], f"{crop}: {product_mismatches([row])}"


def test_a_structural_gate_still_applies_after_migrating() -> None:
    """An unsown pasture has no seeding pass, whatever the table rates."""
    row = upgrade_row({"crop": "Volunteer pasture", "pre_emergent": "Yes"})

    _, changes = neutralise([{**row, "year": 1}])

    assert [c["field"] for c in changes if c["field"] == "Pre-emergent"] == ["Pre-emergent"]


# -- The three sprays are explained where they are chosen --------------------


def test_the_editor_explains_what_the_three_slots_are() -> None:
    """They read as timings unless something says otherwise, and they are not.

    The mechanism is Calcs!P35:P39 counting how many of the three slots name a
    product and Calcs!C168 raising that product's survival to the power of the
    count -- so a second spray of the same thing compounds rather than adds a
    stage. A user cannot infer that from three boxes labelled Spray 1/2/3.
    """
    from utils.year_editor import FIELD_HELP, GROUP_NOTES
    from rim.herbicides import POST_EMERGENT_FIELDS

    note = GROUP_NOTES["Post-emergent sprays"]
    assert "not three timings" in note
    assert "same point" in note

    for field in POST_EMERGENT_FIELDS:
        assert field in FIELD_HELP, f"{field} has no tooltip"
        assert "same point in the season" in FIELD_HELP[field]


def test_the_grid_explains_them_the_same_way() -> None:
    """One string, so the two editors cannot drift apart."""
    import pathlib

    page = pathlib.Path("pages/2_Strategy.py").read_text(encoding="utf-8")

    assert page.count("help=POST_EMERGENT_HELP") == 3
    assert '_YEAR_FIELD_HELP["post_emergent_1"]' in page


def test_the_compounding_matches_the_workbooks_own_arithmetic() -> None:
    """The claim the tooltip makes: twice takes survival from 10% to 1%."""
    from rim.defaults import DEFAULT_OPTIONS, build_default_strategy
    from rim.ryegrass import total_control_fraction

    base = {**build_default_strategy(1)[0], "crop": "Wheat", "pre_emergent": "None",
            "post_emergent_1": "None", "post_emergent_2": "None",
            "post_emergent_3": "None"}

    def survival(**sprays) -> float:
        return 1.0 - total_control_fraction({**base, **sprays}, DEFAULT_OPTIONS, None)

    once = survival(post_emergent_1="Topik")
    twice = survival(post_emergent_1="Topik", post_emergent_2="Topik")

    assert once == pytest.approx(0.10)
    assert twice == pytest.approx(once ** 2), "a repeat squares survival, per Calcs!C168"
