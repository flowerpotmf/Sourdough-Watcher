"""Constants for the Sourdough Monitor integration."""

import json
from pathlib import Path

DOMAIN = "sourdough"
VERSION: str = json.loads(
    (Path(__file__).parent / "manifest.json").read_text()
)["version"]
PLATFORMS = ["sensor"]

# Storage
STORAGE_KEY = f"{DOMAIN}.data"
STORAGE_VERSION = 1

# Unit systems
UNIT_METRIC = "metric"
UNIT_IMPERIAL = "imperial"

# Conversion factors
GRAMS_PER_OZ = 28.3495
# Approximate conversions for volume <-> weight
# These vary by flour type; AP flour is ~120g/cup, water is 240g/cup
GRAMS_PER_CUP_FLOUR = 120.0
GRAMS_PER_CUP_WATER = 240.0
GRAMS_PER_TBSP_FLOUR = GRAMS_PER_CUP_FLOUR / 16
GRAMS_PER_TBSP_WATER = GRAMS_PER_CUP_WATER / 16

# Default recipe values (metric, based on 1/2 cup flour + 1/4 cup water)
# 1/2 cup AP flour ≈ 60g; 1/4 cup water ≈ 60g
DEFAULT_FLOUR_GRAMS = 60.0
DEFAULT_WATER_GRAMS = 60.0
DEFAULT_DISCARD_RATIO = 0.5  # discard 50% before each feeding (Day 3+)
DEFAULT_VESSEL_TARE_GRAMS = 0.0

# Day on which the starter enters the open-ended maintenance phase. From this
# day onward the feeding interval is user-configurable (see
# DEFAULT_MAINTENANCE_INTERVAL_HOURS) rather than fixed by the recipe.
MAINTENANCE_START_DAY = 8

# Default maintenance feeding interval (hours). 12h suits a starter kept at
# room temperature. Bakers who follow a fridge-stored, weekly-feeding routine
# (e.g. Hendrik Kleinwächter's "The Sourdough Framework") can set this to 168h
# (7 days) in the integration's options. Range enforced by the config flow.
DEFAULT_MAINTENANCE_INTERVAL_HOURS = 12.0
MIN_MAINTENANCE_INTERVAL_HOURS = 1.0
MAX_MAINTENANCE_INTERVAL_HOURS = 720.0  # 30 days

# Whether to discard part of the starter before each maintenance feeding.
# A room-temperature starter is usually discarded down (True). Some
# fridge-stored, weekly routines keep a small amount instead of discarding —
# set this to False to drop the discard step (and its alerts) in maintenance.
DEFAULT_MAINTENANCE_DISCARD = True

# Convenience presets surfaced by the "Maintenance cadence" select entity,
# mapping a human label to an interval in hours.
MAINTENANCE_PRESETS = {
    "Twice daily (12h)": 12.0,
    "Daily (24h)": 24.0,
    "Every 2 days (48h)": 48.0,
    "Weekly — fridge (168h)": 168.0,
}

# Recipe phase definitions for the fixed establishment period:
# (min_day, max_day, interval_hours, discard). Day MAINTENANCE_START_DAY and
# beyond are handled separately so the interval can be customised.
RECIPE_PHASES = [
    (1, 2, 24, False),   # Days 1-2: feed every 24h, no discard
    (3, 5, 24, True),    # Days 3-5: discard half, feed every 24h
    (6, 7, 12, True),    # Days 6-7: discard half, feed every 12h
]

# Configuration keys
CONF_VESSEL_TARE = "vessel_tare_g"
CONF_FLOUR_AMOUNT = "flour_g"
CONF_WATER_AMOUNT = "water_g"
CONF_DISCARD_RATIO = "discard_ratio"
CONF_UNIT_SYSTEM = "unit_system"
CONF_START_DATETIME = "start_datetime"
CONF_MAINTENANCE_INTERVAL_HOURS = "maintenance_interval_hours"
CONF_MAINTENANCE_DISCARD = "maintenance_discard"

# Service names
SERVICE_RECORD_FEEDING = "record_feeding"
SERVICE_RESET = "reset_process"
SERVICE_SET_DAY = "set_day"
SERVICE_SET_WEIGHT = "set_weight"
SERVICE_SKIP_FEEDING = "skip_feeding"

# Sensor unique ID suffixes
SENSOR_DAY = "day"
SENSOR_PHASE = "phase"
SENSOR_NEXT_FEEDING = "next_feeding"
SENSOR_LAST_FED = "last_fed"
SENSOR_STARTER_WEIGHT = "starter_weight"
SENSOR_TOTAL_WEIGHT = "total_weight"
SENSOR_VESSEL_TARE = "vessel_tare"
SENSOR_FLOUR_TO_ADD = "flour_to_add"
SENSOR_WATER_TO_ADD = "water_to_add"
SENSOR_DISCARD_AMOUNT = "discard_amount"
SENSOR_INSTRUCTIONS = "instructions"
SENSOR_FEEDING_COUNT = "feeding_count"
SENSOR_HYDRATION = "hydration"
