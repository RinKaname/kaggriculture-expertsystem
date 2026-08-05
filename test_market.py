import pytest
import math
from src.market import (
    shape_func,
    compute_market_price,
    compute_bulk_sell_revenue,
    project_town_consumption
)
from src.constants import PRICE_FLOOR, PRODUCTS, SHOPS, TOWN_CENTER_PRODUCTS, TOWN_CENTER_DEMAND_SCHEDULE

def test_shape_func():
    # Test positive values
    assert shape_func("linear", 4.0) == 4.0
    assert shape_func("sq", 3.0) == 9.0
    assert shape_func("sqrt", 16.0) == 4.0
    assert math.isclose(shape_func("log", 4.0), math.log(5.0))
    assert math.isclose(shape_func("log10", 9.0), math.log10(10.0))

    # Test unknown fallback to linear
    assert shape_func("unknown_func", 5.0) == 5.0

    # Test negative values (should clamp to 0.0)
    assert shape_func("linear", -5.0) == 0.0
    assert shape_func("sq", -1.0) == 0.0
    assert shape_func("sqrt", -10.0) == 0.0
    assert shape_func("log", -2.0) == 0.0
    assert shape_func("log10", -3.0) == 0.0

    # Test 0.0
    assert shape_func("linear", 0.0) == 0.0
    assert shape_func("sq", 0.0) == 0.0
    assert shape_func("sqrt", 0.0) == 0.0
    assert shape_func("log", 0.0) == 0.0
    assert shape_func("log10", 0.0) == 0.0

def test_compute_market_price():
    # Create custom params for testing
    custom_params = {
        "TestItem": {
            "base": 100,
            "I0": 50,
            "T": 50,
            "below_func": "linear",
            "below_target": 2.0, # This implies amp = 2.0 * 100 / 50 = 4.0
            "above_func": "linear",
            "above_target": 0.5, # This implies amp = 0.5 * 100 / 50 = 1.0
        }
    }

    # Test inventory exactly at I0
    price = compute_market_price("TestItem", 50, params=custom_params)
    assert price == 100 # base price

    # Test inventory < I0 (price spike)
    # amp = 4.0, inventory = 40, shape(I0 - inventory) = 10
    # price = 100 + 4.0 * 10 = 140
    price_below = compute_market_price("TestItem", 40, params=custom_params)
    assert price_below == 140

    # Test inventory > I0 (price decay)
    # amp = 1.0, inventory = 60, shape(inventory - I0) = 10
    # price = 100 - 1.0 * 10 = 90
    price_above = compute_market_price("TestItem", 60, params=custom_params)
    assert price_above == 90

    # Test extreme price decay (should hit PRICE_FLOOR)
    # amp = 1.0, inventory = 200, shape(inventory - I0) = 150
    # price = 100 - 1.0 * 150 = -50 => should be floored to PRICE_FLOOR
    price_extreme = compute_market_price("TestItem", 200, params=custom_params)
    assert price_extreme == PRICE_FLOOR

def test_compute_bulk_sell_revenue():
    # Create custom params for testing
    custom_params = {
        "TestItem": {
            "base": 100,
            "I0": 50,
            "T": 50,
            "below_func": "linear",
            "below_target": 2.0, # This implies amp = 2.0 * 100 / 50 = 4.0
            "above_func": "linear",
            "above_target": 0.5, # This implies amp = 0.5 * 100 / 50 = 1.0
        }
    }

    # Test 0 quantity
    rev, inv = compute_bulk_sell_revenue("TestItem", 50, 0, params=custom_params)
    assert rev == 0
    assert inv == 50

    # Test negative quantity
    rev, inv = compute_bulk_sell_revenue("TestItem", 50, -5, params=custom_params)
    assert rev == 0
    assert inv == 50

    # Test bulk selling with price depression (slippage)
    # 1st item at inv=50 -> price=100
    # 2nd item at inv=51 -> price=100 - 1.0 * (51-50) = 99
    # 3rd item at inv=52 -> price=100 - 1.0 * (52-50) = 98
    # Total revenue = 100 + 99 + 98 = 297
    rev, inv = compute_bulk_sell_revenue("TestItem", 50, 3, params=custom_params)
    assert rev == 297
    assert inv == 53

    # Test bulk selling that hits the price floor and verifies inventory stops incrementing properly
    # If we sell enough to drop price below floor, compute_bulk_sell_revenue still adds price but
    # only increments inventory if price > PRICE_FLOOR
    # In our custom params, price hits 0 when inventory is 150.
    # At inventory 149: price = 100 - 1.0 * (149-50) = 1.
    # So if PRICE_FLOOR is 1, any sale starting from inventory 149 will just yield PRICE_FLOOR per unit.

    # Let's test a sequence where the price floor is hit mid-sale.
    # Let PRICE_FLOOR = 1 (imported from constants).
    # inv=148, price = 100 - 98 = 2. inventory increments to 149.
    # inv=149, price = 100 - 99 = 1. Because price > PRICE_FLOOR is FALSE (1 > 1 is False),
    # inventory stays at 149 for the next iteration!
    # inv=149, price = 1.
    # Total for 3 items starting at inv=148: 2 + 1 + 1 = 4.
    rev, inv = compute_bulk_sell_revenue("TestItem", 148, 3, params=custom_params)
    assert rev == 4
    assert inv == 149

def test_project_town_consumption(monkeypatch):
    # Using monkeypatch to isolate our tests from potential constant changes

    mock_PRODUCTS = ["Apples", "Bananas", "Cherries", "Wood", "Stone"]
    mock_SHOPS = {
        "FruitShop": ["Apples", "Bananas"], # multi-product shop
        "AppleStand": ["Apples"],           # single-product shop
        "Lumberjack": ["Wood"]              # single-product shop
    }
    mock_TOWN_CENTER_PRODUCTS = ["Apples", "Wood"]
    mock_TOWN_CENTER_DEMAND_SCHEDULE = [
        (20, 4),
        (10, 2),
        (0, 1)
    ]

    monkeypatch.setattr("src.market.PRODUCTS", mock_PRODUCTS)
    monkeypatch.setattr("src.market.SHOPS", mock_SHOPS)
    monkeypatch.setattr("src.market.TOWN_CENTER_PRODUCTS", mock_TOWN_CENTER_PRODUCTS)
    monkeypatch.setattr("src.market.TOWN_CENTER_DEMAND_SCHEDULE", mock_TOWN_CENTER_DEMAND_SCHEDULE)

    # Test Day 0 (multiplier 1x)
    # Shop consumption:
    # - AppleStand (single, Apples): 6 * 2 = 12
    # - FruitShop (multi, Apples & Bananas): 6 * 1 = 6 (each)
    # - Lumberjack (single, Wood): 6 * 2 = 12
    # Total Shop Apples: 12 + 6 = 18. Bananas: 6. Wood: 12.
    # Town Center:
    # - Apples & Wood: 2 * 1 = 2 (each)
    # Total combined:
    # Apples: 18 + 2 = 20
    # Bananas: 6 + 0 = 6
    # Wood: 12 + 2 = 14
    # Cherries: 0
    # Stone: 0
    unlocked_shops = ["FruitShop", "AppleStand", "Lumberjack"]
    consumption_day_0 = project_town_consumption(unlocked_shops, 0, days_ahead=1)
    assert consumption_day_0["Apples"] == 20
    assert consumption_day_0["Bananas"] == 6
    assert consumption_day_0["Wood"] == 14
    assert consumption_day_0["Cherries"] == 0
    assert consumption_day_0["Stone"] == 0

    # Test Day 15 (multiplier 2x)
    # Shop consumption remains the same.
    # Town Center:
    # - Apples & Wood: 2 * 2 = 4 (each)
    # Total combined:
    # Apples: 18 + 4 = 22
    # Bananas: 6 + 0 = 6
    # Wood: 12 + 4 = 16
    consumption_day_15 = project_town_consumption(unlocked_shops, 15, days_ahead=1)
    assert consumption_day_15["Apples"] == 22
    assert consumption_day_15["Bananas"] == 6
    assert consumption_day_15["Wood"] == 16

    # Test Day 25 (multiplier 4x)
    # Shop consumption remains the same.
    # Town Center:
    # - Apples & Wood: 2 * 4 = 8 (each)
    # Total combined:
    # Apples: 18 + 8 = 26
    # Bananas: 6 + 0 = 6
    # Wood: 12 + 8 = 20
    consumption_day_25 = project_town_consumption(unlocked_shops, 25, days_ahead=1)
    assert consumption_day_25["Apples"] == 26
    assert consumption_day_25["Bananas"] == 6
    assert consumption_day_25["Wood"] == 20

    # Test `days_ahead` scaling
    # Should just be exactly twice the Day 25 result
    consumption_day_25_ahead_2 = project_town_consumption(unlocked_shops, 25, days_ahead=2)
    assert consumption_day_25_ahead_2["Apples"] == 52
    assert consumption_day_25_ahead_2["Bananas"] == 12
    assert consumption_day_25_ahead_2["Wood"] == 40

    # Test ignoring non-existent shop in unlocked_shops
    unlocked_shops_with_unknown = ["AppleStand", "UnknownShop"]
    # AppleStand (single, Apples) -> 12
    # Town center at Day 5 -> 2 for Apples and Wood
    # Total Apples: 12 + 2 = 14. Wood: 2.
    consumption_unknown = project_town_consumption(unlocked_shops_with_unknown, 5, days_ahead=1)
    assert consumption_unknown["Apples"] == 14
    assert consumption_unknown["Wood"] == 2
