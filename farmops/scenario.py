"""Harvest-week scenario for a single Indiana grain farm.

All numbers are illustrative, not measured. Swap in real farm data later.
"""

DAYS = ["Mon", "Tue", "Wed"]          # rain arrives Thursday morning
YIELD_BU_PER_ACRE = 190               # corn

FIELDS = {
    # name: acres
    "North 150":  150,
    "Creek 200":  200,
    "Home 120":   120,
    "West 180":   180,
}

COMBINES = {
    # name: acres per hour
    "Combine 1": 9,
    "Combine 2": 9,
}

# Human constraint: max hours one operator can run a combine per day (fatigue cap)
OPERATOR_HOURS_NORMAL = 12
OPERATOR_HOURS_OVERTIME = 14          # hard ceiling, never above this

# Legal constraint: truck drivers limited to 11 driving hours per day (FMCSA hours-of-service)
TRUCKS = 5
DRIVER_HOURS_PER_DAY = 11
BU_PER_TRUCK_HOUR = 900               # round trips to elevator, averaged

# Physical constraints: elevator intake and on-farm bin/dryer capacity
ELEVATOR_BU_PER_DAY = {"Mon": 50000, "Tue": 40000, "Wed": 55000}   # Tue backed up
ON_FARM_DRYER_BU_PER_DAY = 12000

# Costs
OVERTIME_COST_PER_HOUR = 85
RENTAL_COMBINE_COST_PER_DAY = 2400
GRAIN_PRICE_PER_BU = 4.10             # value of grain left in the field when the rain hits

# Knowledge the agents draw on
FAULT_CODES = {
    "HYD-217": {"component": "hydraulic pump seal", "repair_hours": 4,
                "part": "PS-4410 seal kit", "safety": "Hydraulic leak: lockout/tagout before inspection."},
    "ENG-102": {"component": "coolant temp sensor", "repair_hours": 1,
                "part": "CT-88 sensor", "safety": None},
}

PARTS_SUPPLIERS = {
    "PS-4410 seal kit": [
        {"supplier": "Lafayette dealer", "in_stock": True,  "eta_hours": 3,  "cost": 310},
        {"supplier": "Online OEM",       "in_stock": True,  "eta_hours": 48, "cost": 240},
    ],
    "CT-88 sensor": [
        {"supplier": "Lafayette dealer", "in_stock": True,  "eta_hours": 2,  "cost": 95},
    ],
}

RENTAL_COMBINES = [{"provider": "Tippecanoe Ag Rental", "available_from_day": "Tue", "acres_per_hour": 9}]

TECHNICIANS = {
    "Dave":  {"certified": ["hydraulic", "engine"], "free_from_hour": 8},
    "Priya": {"certified": ["engine"],              "free_from_hour": 6},
}
