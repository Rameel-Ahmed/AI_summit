"""Symbolic core: CP-SAT finds a guaranteed-feasible harvest plan under legal, physical and human limits."""
from ortools.sat.python import cp_model

from . import scenario as S


def hours_available(cap, ready_hour, day_idx):
    """Work day runs 6am-8pm. ready_hour is hours after 6am Monday the machine comes back."""
    if ready_hour is None:
        return cap
    offset = ready_hour - 24 * day_idx
    return max(0, min(cap, cap - max(0, offset)))


def solve(bb, name, overtime=False, rent=False):
    c = bb.constraints
    days = c["days"]
    fields = c["fields"]
    cap = S.OPERATOR_HOURS_OVERTIME if overtime else S.OPERATOR_HOURS_NORMAL

    combines = dict(S.COMBINES)
    ready = {k: None for k in combines}
    if c.get("down_machine"):
        ready[c["down_machine"]] = c["back_online_hour"]
    if rent:
        r = c["rental_option"]
        combines["Rental"] = r["acres_per_hour"]
        ready["Rental"] = 24 * days.index(r["available_from_day"]) if r["available_from_day"] in days else 999

    m = cp_model.CpModel()
    h = {(k, f, d): m.NewIntVar(0, cap, f"h_{k}_{f}_{d}") for k in combines for f in fields for d in days}

    for k in combines:
        for di, d in enumerate(days):
            m.Add(sum(h[k, f, d] for f in fields) <= hours_available(cap, ready[k], di))

    acres = {}
    for f, a in fields.items():
        acres[f] = m.NewIntVar(0, a, f"acres_{f}")
        m.Add(acres[f] <= sum(combines[k] * h[k, f, d] for k in combines for d in days))

    # Bushels per day limited by trucking (legal HOS) and by storage (physical)
    for d in days:
        bu = sum(S.YIELD_BU_PER_ACRE * combines[k] * h[k, f, d] for k in combines for f in fields)
        m.Add(bu <= c["haul_bu_per_day"])
        m.Add(bu <= c["storage_bu_per_day"][d])

    ot_hours = []
    if overtime:
        for k in combines:
            for d in days:
                ot = m.NewIntVar(0, cap, f"ot_{k}_{d}")
                m.Add(ot >= sum(h[k, f, d] for f in fields) - S.OPERATOR_HOURS_NORMAL)
                ot_hours.append(ot)

    rental_days = sum(1 for di, d in enumerate(days) if rent and 24 * di >= ready.get("Rental", 999))
    fixed_cost = c.get("part_cost", 0) + rental_days * S.RENTAL_COMBINE_COST_PER_DAY

    value_per_acre = int(S.YIELD_BU_PER_ACRE * S.GRAIN_PRICE_PER_BU)
    prio = set(c.get("priorities") or [])
    m.Maximize(sum((value_per_acre + (50 if f in prio else 0)) * acres[f] for f in fields)
               - S.OVERTIME_COST_PER_HOUR * sum(ot_hours)
               - sum(h.values()))                     # tiny tie-breaker: don't burn idle hours

    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = 5
    status = sol.StatusName(sol.Solve(m))
    if status not in ("OPTIMAL", "FEASIBLE"):
        return {"name": name, "status": status}

    total = sum(fields.values())
    done = sum(sol.Value(acres[f]) for f in fields)
    extra = fixed_cost + S.OVERTIME_COST_PER_HOUR * sum(sol.Value(o) for o in ot_hours)
    schedule = {d: {k: {f: sol.Value(h[k, f, d]) for f in fields if sol.Value(h[k, f, d])}
                    for k in combines} for d in days}
    budget = c.get("budget_limit")
    return {
        "name": name, "status": status,
        "acres_total": total, "acres_done": done, "acres_at_risk": total - done,
        "grain_at_risk": int((total - done) * value_per_acre),
        "extra_cost": int(extra),
        "over_budget": bool(budget and extra > budget),
        "schedule": schedule,
    }
