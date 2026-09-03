"""Herbicides are named, and what they do depends on the crop.

The app used to ask "pre-emergent? yes/no" and apply a flat 45%. RIM names five
pre-emergent and five post-emergent products and rates each one per crop, in
``Calcs!N54:T97``. A single number cannot be right for all of them, and the
crop-dependence is the part that matters agronomically: Topik is a
grass-selective cereal herbicide, so it takes 90% of the ryegrass in wheat and
nothing whatever in canola.

Every rule below re-reads the generated table it depends on, so a rule cannot
outlive its evidence. If ``tools/extract_params.py`` is rerun and a number
moves, these fail rather than quietly asserting yesterday's workbook.
"""
from __future__ import annotations

import json

import pytest

from rim import herbicides
from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PROFILE, build_default_strategy
from rim.engine import simulate_strategy
from rim.rotation import APP_CROP_CODE, CROP_CODE, app_crop_code
from rim.ryegrass import total_control_fraction
from utils.applicability import neutralise, product_options

WHEAT, BARLEY, CANOLA, LEGUME, VOLUNTEER, CLOVER, CADIZ = range(7)


@pytest.fixture(scope="module")
def table() -> dict:
    """The generated control table, read independently of rim.herbicides."""
    with open(herbicides.DATA_PATH, encoding="utf-8") as handle:
        return json.load(handle)["options"]


# ── The products are the workbook's, not ours ─────────────────────────────────


def test_the_products_are_read_from_the_generated_table(table) -> None:
    for product in herbicides.pre_emergents() + herbicides.post_emergents():
        label = table[str(product.row)]["label"]
        assert label.endswith(product.name), f"row {product.row}: {label}"
        assert product.control == {
            int(code): float(value)
            for code, value in table[str(product.row)]["by_crop_code"].items()
        }


def test_the_workbook_offers_five_of_each() -> None:
    assert len(herbicides.pre_emergents()) == 5
    assert len(herbicides.post_emergents()) == 5


def test_the_dropdowns_lead_with_not_spraying() -> None:
    assert herbicides.pre_emergent_names()[0] == herbicides.NONE
    assert herbicides.post_emergent_names()[0] == herbicides.NONE
    assert "Sakura" in herbicides.pre_emergent_names()
    assert "Clethodim" in herbicides.post_emergent_names()


# ── A zero is a statement about the crop ──────────────────────────────────────


@pytest.mark.parametrize(
    "product, slot, works, does_not",
    [
        ("Topik", "post", (WHEAT, BARLEY), (CANOLA, LEGUME, VOLUNTEER, CLOVER, CADIZ)),
        ("Hussar", "post", (WHEAT, BARLEY), (CANOLA, LEGUME, VOLUNTEER)),
        ("Clethodim", "post", (CANOLA, LEGUME), (WHEAT, BARLEY, VOLUNTEER)),
        ("Glyphosate", "post", (CANOLA, LEGUME), (WHEAT, BARLEY, VOLUNTEER)),
        ("Paraquat", "post", (VOLUNTEER, CLOVER, CADIZ), (WHEAT, BARLEY, CANOLA)),
        ("Propyzamide", "pre", (CANOLA, LEGUME), (WHEAT, BARLEY, VOLUNTEER)),
        ("Triazine", "pre", (CANOLA, VOLUNTEER, CLOVER), (WHEAT, BARLEY)),
        ("Sakura", "pre", (WHEAT, BARLEY, CANOLA, LEGUME), (VOLUNTEER, CLOVER, CADIZ)),
    ],
)
def test_a_product_works_only_where_the_workbook_says(product, slot, works, does_not, table) -> None:
    rows = (herbicides.PRE_EMERGENT_ROWS if slot == "pre"
            else herbicides.POST_EMERGENT_ROWS)
    row = next(r for r in rows if table[str(r)]["label"].endswith(product))
    by_crop = table[str(row)]["by_crop_code"]

    for code in works:
        assert herbicides.works_on(product, code, slot=slot)
        assert float(by_crop[str(code)]) > 0.0, "the table disagrees with this test"
    for code in does_not:
        assert not herbicides.works_on(product, code, slot=slot)
        assert float(by_crop[str(code)]) == 0.0, "the table disagrees with this test"


def test_nothing_sprayed_controls_nothing() -> None:
    for slot in ("pre", "post"):
        assert herbicides.control(herbicides.NONE, WHEAT, slot=slot) == 0.0
        assert herbicides.control(None, WHEAT, slot=slot) == 0.0
        assert herbicides.control("", WHEAT, slot=slot) == 0.0


def test_a_product_this_build_does_not_know_controls_nothing() -> None:
    """A plan from a later version degrades to "not sprayed", never crashes."""
    assert herbicides.control("Nonesuch 500EC", WHEAT, slot="pre") == 0.0
    assert herbicides.find("Nonesuch 500EC", slot="post") is None


# ── The crop codes the strategy rows actually use ─────────────────────────────


def test_app_crop_labels_agree_with_the_workbook_codes() -> None:
    """The app spells crops out; CROP_CODE keys are the workbook's shorthand.

    Looking an app label up in CROP_CODE returns Wheat for everything, silently,
    which is how the first cut of this got pasture herbicides wrong.
    """
    from rim.excel_inputs import CROP_LABELS

    assert APP_CROP_CODE == {
        app: CROP_CODE[workbook] for workbook, app in CROP_LABELS.items()
    }
    assert app_crop_code("Volunteer pasture") == VOLUNTEER
    assert app_crop_code("Volunt.") == WHEAT, "workbook labels are not app labels"


# ── What the editor offers ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "crop, field, expected",
    [
        ("Wheat", "post_emergent_1", ["None", "Topik", "Hussar"]),
        ("Canola", "post_emergent_1", ["None", "Clethodim", "Glyphosate"]),
        ("Volunteer pasture", "post_emergent_2", ["None", "Paraquat"]),
        ("Volunteer pasture", "pre_emergent", ["None", "Triazine"]),
    ],
)
def test_only_products_that_do_something_are_offered(crop, field, expected) -> None:
    assert product_options(field, crop) == expected


def test_every_offered_product_actually_works_on_that_crop() -> None:
    for crop in APP_CROP_CODE:
        for field, slot in (("pre_emergent", "pre"), ("post_emergent_1", "post")):
            offered = product_options(field, crop)[1:]   # drop "None"
            assert offered == [
                name for name in offered
                if herbicides.works_on(name, app_crop_code(crop), slot=slot)
            ]


def test_the_offer_narrows_to_what_the_crop_can_use() -> None:
    """Cadiz keeps the one pre-emergent rated for it, and loses the other four."""
    assert product_options("pre_emergent", "Cadiz pasture") == ["None", "Triazine"]
    assert product_options("post_emergent_1", "Wheat")[1:] == ["Topik", "Hussar"]


# ── Choosing one that cannot work is caught, not silently ignored ─────────────


def _plan(**overrides) -> list[dict]:
    row = {**build_default_strategy(1)[0], "year": 1}
    row.update(overrides)
    return [row]


def test_a_product_that_does_nothing_here_is_cleared_and_reported() -> None:
    cleaned, changes = neutralise(_plan(crop="Canola", post_emergent_1="Topik"))

    assert cleaned[0]["post_emergent_1"] == herbicides.NONE
    assert len(changes) == 1
    assert changes[0]["choice"] == "Topik"
    assert "canola" in changes[0]["reason"]


def test_a_product_that_works_here_is_left_alone() -> None:
    cleaned, changes = neutralise(_plan(crop="Canola", post_emergent_1="Clethodim"))

    assert cleaned[0]["post_emergent_1"] == "Clethodim"
    assert [c for c in changes if c["field"].startswith("Post-emergent")] == []


# ── The engine actually responds to the choice ────────────────────────────────


def _control(crop: str, **sprays) -> float:
    row = {**build_default_strategy(1)[0], "crop": crop,
           "pre_emergent": herbicides.NONE,
           "post_emergent_1": herbicides.NONE, **sprays}
    return total_control_fraction(row, DEFAULT_OPTIONS, None)


def test_the_same_spray_does_different_things_in_different_crops() -> None:
    """The whole point of naming the product."""
    in_wheat = _control("Wheat", post_emergent_1="Topik")
    in_canola = _control("Canola", post_emergent_1="Topik")
    nothing_in_canola = _control("Canola")

    assert in_wheat > in_canola
    assert in_canola == pytest.approx(nothing_in_canola), (
        "Topik is rated 0 on canola, so choosing it must change nothing"
    )


def test_a_stronger_product_controls_more() -> None:
    """Hussar is 0.95 in wheat where Topik is 0.90 — the app must show that."""
    assert herbicides.control("Hussar", WHEAT, slot="post") > \
           herbicides.control("Topik", WHEAT, slot="post")
    assert _control("Wheat", post_emergent_1="Hussar") > \
           _control("Wheat", post_emergent_1="Topik")


def test_three_slots_stack() -> None:
    """2.Strategy rows 11-13 are three applications, not one repeated."""
    one = _control("Wheat", post_emergent_1="Topik")
    two = _control("Wheat", post_emergent_1="Topik", post_emergent_2="Hussar")

    assert two > one


def test_the_choice_reaches_the_seed_bank() -> None:
    """Not just the control fraction — the number a user actually reads."""
    def final_seed_bank(product: str) -> float:
        rows = [dict(row, crop="Wheat", pre_emergent=herbicides.NONE,
                     post_emergent_1=product, post_emergent_2=herbicides.NONE,
                     post_emergent_3=herbicides.NONE)
                for row in build_default_strategy(10)]
        result = simulate_strategy(
            profile=DEFAULT_PROFILE, prices={}, options=DEFAULT_OPTIONS,
            strategy_rows=rows,
        )
        return float(result["yearly"]["seed_bank_end"].iloc[-1])

    assert final_seed_bank("Hussar") < final_seed_bank("Topik") < final_seed_bank(herbicides.NONE)


# ── Plans saved before products existed ───────────────────────────────────────


def test_a_bare_yes_becomes_a_product_that_works_on_that_crop() -> None:
    for crop in APP_CROP_CODE:
        upgraded = herbicides.upgrade_row(
            {"crop": crop, "pre_emergent": "Yes", "post_emergent": "Yes"}
        )
        code = app_crop_code(crop)
        for field, slot in (("pre_emergent", "pre"), ("post_emergent_1", "post")):
            choice = upgraded[field]
            assert choice == herbicides.NONE or herbicides.works_on(choice, code, slot=slot), (
                f"{crop}: {field} upgraded to {choice}, which does nothing there"
            )


def test_a_no_becomes_not_sprayed() -> None:
    upgraded = herbicides.upgrade_row(
        {"crop": "Wheat", "pre_emergent": "No", "post_emergent": "No"}
    )
    assert upgraded["pre_emergent"] == herbicides.NONE
    assert all(upgraded[f] == herbicides.NONE for f in herbicides.POST_EMERGENT_FIELDS)


def test_the_old_single_slot_becomes_the_first_of_three() -> None:
    upgraded = herbicides.upgrade_row(
        {"crop": "Wheat", "pre_emergent": "No", "post_emergent": "Yes"}
    )
    assert "post_emergent" not in upgraded
    assert upgraded["post_emergent_1"] != herbicides.NONE
    assert upgraded["post_emergent_2"] == herbicides.NONE
    assert upgraded["post_emergent_3"] == herbicides.NONE


def test_a_row_at_the_current_schema_is_untouched() -> None:
    """Upgrading must be idempotent, or it would rewrite live plans."""
    row = herbicides.upgrade_row(
        {"crop": "Wheat", "pre_emergent": "Sakura", "post_emergent_1": "Hussar"}
    )

    assert herbicides.upgrade_row(row) == row
    assert row["pre_emergent"] == "Sakura"
    assert row["post_emergent_1"] == "Hussar"


def test_the_engine_still_runs_a_version_one_plan() -> None:
    """Old fixtures and old save files must not silently lose their control."""
    old = [dict(row, pre_emergent="Yes", post_emergent="Yes") for row in build_default_strategy(3)]
    for row in old:
        row.pop("post_emergent_1", None)
        row.pop("post_emergent_2", None)
        row.pop("post_emergent_3", None)

    result = simulate_strategy(
        profile=DEFAULT_PROFILE, prices={}, options=DEFAULT_OPTIONS, strategy_rows=old,
    )

    assert len(result["yearly"]) == 3
    sprayed = simulate_strategy(
        profile=DEFAULT_PROFILE, prices={}, options=DEFAULT_OPTIONS,
        strategy_rows=[dict(r, pre_emergent="No", post_emergent="No") for r in old],
    )
    assert float(result["yearly"]["seed_bank_end"].iloc[-1]) < \
           float(sprayed["yearly"]["seed_bank_end"].iloc[-1]), (
        "a version-1 'Yes' must still control ryegrass"
    )


def test_the_defaults_name_real_products() -> None:
    row = build_default_strategy(1)[0]

    assert herbicides.find(row["pre_emergent"], slot="pre") is not None
    assert herbicides.find(row["post_emergent_1"], slot="post") is not None
    assert herbicides.works_on(row["pre_emergent"], app_crop_code(row["crop"]), slot="pre")


# ── Each spray is a pass over the paddock, and a cost ─────────────────────────


def _herbicide_cost(**sprays) -> float:
    from rim.defaults import DEFAULT_PRICES
    from rim.economics import compute_costs

    row = {**build_default_strategy(1)[0], "pre_emergent": herbicides.NONE,
           "post_emergent_1": herbicides.NONE, "post_emergent_2": herbicides.NONE,
           "post_emergent_3": herbicides.NONE, **sprays}
    return compute_costs(row, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0)["herbicide_cost"]


def test_each_product_is_charged_at_the_workbook_s_own_price() -> None:
    """Calcs!N105:T147, not a flat pass: Topik is $13/ha in wheat, Hussar $38."""
    from rim import control_options

    topik = control_options.cost("post_emergent_1", "Topik", WHEAT)
    hussar = control_options.cost("post_emergent_1", "Hussar", WHEAT)

    assert topik != hussar, "the whole point of pricing per product"
    assert _herbicide_cost() == 0.0
    assert _herbicide_cost(post_emergent_1="Topik") == pytest.approx(topik)
    assert _herbicide_cost(post_emergent_1="Hussar") == pytest.approx(hussar)


def test_every_slot_filled_is_charged(WHEAT=WHEAT) -> None:
    """Three post-emergent sprays are three applications, each at its own price."""
    from rim import control_options

    priced = sum(control_options.cost("post_emergent_1", name, WHEAT)
                 for name in ("Topik", "Hussar", "Topik"))

    assert _herbicide_cost(post_emergent_1="Topik", post_emergent_2="Hussar",
                           post_emergent_3="Topik") == pytest.approx(priced)


def test_the_same_product_costs_differently_by_crop() -> None:
    """Glyphosate knock-down is $26/ha in a crop and $22/ha in a pasture."""
    from rim import control_options

    in_crop = control_options.cost("knockdown", "Glyphosate", WHEAT)
    in_pasture = control_options.cost("knockdown", "Glyphosate", VOLUNTEER)

    assert in_crop != in_pasture
    assert _herbicide_cost(knockdown="Glyphosate") == pytest.approx(in_crop)


def test_a_version_one_row_is_still_charged_for_its_spray() -> None:
    """Otherwise an old plan would spray for free the moment the field moved."""
    old = herbicides.upgrade_row({**build_default_strategy(1)[0],
                                  "pre_emergent": "No", "post_emergent": "Yes"})

    assert _herbicide_cost(**{k: v for k, v in old.items()
                              if k in herbicides.POST_EMERGENT_FIELDS}) > 0.0
