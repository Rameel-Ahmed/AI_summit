"""Specialist agents. Each one turns its domain knowledge into constraints on the shared blackboard."""
import time

from . import llm
from . import scenario as S

ALL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


class Admin:
    """Neural in: supervisor's order -> facts every other agent can use."""
    name = "Admin"

    def handle_order(self, bb, order):
        facts, source = llm.parse_order(order)
        bb.say(self.name, f"parsed order via {source}: {facts}")
        rain = facts.get("rain_day") or "Thu"
        days = ALL_DAYS[:ALL_DAYS.index(rain)] if rain in ALL_DAYS else S.DAYS
        bb.post(self.name, "days", days, f"rain arrives {rain}", authority="USER_ASSERTED")
        bb.post(self.name, "budget_limit", facts.get("budget_limit"), authority="USER_ASSERTED")
        bb.post(self.name, "priorities", facts.get("priorities") or [], authority="USER_ASSERTED")
        bb.post(self.name, "elevator_backed_up", bool(facts.get("elevator_backed_up")), authority="USER_ASSERTED")
        return facts


class Diagnostics:
    """Watchdog: reads machine fault codes, and checks that every agent is alive and sane."""
    name = "Diagnostics"

    def inspect(self, bb, facts):
        for code in facts.get("fault_codes", []):
            info = S.FAULT_CODES.get(code)
            if not info:
                bb.alert(f"Unknown fault code {code}: send a human to inspect before running.")
                continue
            machine = (facts.get("down_machines") or ["Combine 2"])[0]
            bb.post(self.name, "down_machine", machine, f"{code} = {info['component']}", authority="INFERRED")
            bb.post(self.name, "repair_hours", info["repair_hours"], "p50 estimate", authority="PREDICTED")
            bb.post(self.name, "part_needed", info["part"])
            bb.post(self.name, "skill_needed", "hydraulic" if code.startswith("HYD") else "engine")
            if info["safety"]:
                bb.alert(f"SAFETY ({machine}): {info['safety']}")

    def watch(self, bb, expected_agents, results, max_silence_s=5.0):
        now = time.time()
        for a in expected_agents:
            last = bb.heartbeats.get(a)
            if last is None or now - last > max_silence_s:
                bb.alert(f"WATCHDOG: {a} agent has not reported. Plan may be missing its constraints.")
        for r in results:
            if r["status"] not in ("OPTIMAL", "FEASIBLE"):
                bb.alert(f"WATCHDOG: '{r['name']}' has no feasible plan. Constraints conflict, needs a human.")
        bb.beat(self.name)


class Technician:
    name = "Technician"

    def plan_repair(self, bb):
        skill = bb.constraints.get("skill_needed")
        if not skill:
            bb.say(self.name, "no repair needed")
            return
        techs = [(n, t) for n, t in S.TECHNICIANS.items() if skill in t["certified"]]
        if not techs:
            bb.alert(f"No certified {skill} technician available.")
            return
        name, t = min(techs, key=lambda x: x[1]["free_from_hour"])
        bb.post(self.name, "tech_assigned", name, f"certified {skill}")
        bb.post(self.name, "tech_free_hour", t["free_from_hour"] - 6, "hours after 6am Mon")


class Procurement:
    name = "Procurement"

    def source(self, bb):
        part = bb.constraints.get("part_needed")
        if part:
            offers = [o for o in S.PARTS_SUPPLIERS.get(part, []) if o["in_stock"]]
            best = min(offers, key=lambda o: o["eta_hours"])
            bb.post(self.name, "part_eta_hours", best["eta_hours"], f"{best['supplier']}, ${best['cost']}", authority="VERIFIED")
            bb.post(self.name, "part_cost", best["cost"])
        rental = S.RENTAL_COMBINES[0]
        bb.post(self.name, "rental_option", rental, f"${S.RENTAL_COMBINE_COST_PER_DAY}/day")


class Logistics:
    name = "Logistics"

    def capacity(self, bb):
        haul = S.TRUCKS * S.DRIVER_HOURS_PER_DAY * S.BU_PER_TRUCK_HOUR
        bb.post(self.name, "haul_bu_per_day", haul,
                f"{S.TRUCKS} trucks x {S.DRIVER_HOURS_PER_DAY}h HOS limit")
        elevator = dict(S.ELEVATOR_BU_PER_DAY)
        if bb.constraints.get("elevator_backed_up"):
            elevator = {d: int(v * 0.7) for d, v in elevator.items()}
        bb.post(self.name, "storage_bu_per_day",
                {d: elevator.get(d, 15000) + S.ON_FARM_DRYER_BU_PER_DAY for d in bb.constraints["days"]},
                "elevator intake + on-farm dryer", authority="PREDICTED")


class Ops:
    name = "Ops"

    def __init__(self, fields=None):
        self.fields = fields or S.FIELDS

    def availability(self, bb):
        """Hours each combine can run each day, given repair timing."""
        down = bb.constraints.get("down_machine")
        ready = None
        if down:
            ready = max(bb.constraints.get("part_eta_hours", 0),
                        bb.constraints.get("tech_free_hour", 0)) + bb.constraints.get("repair_hours", 0)
            bb.post(self.name, "back_online_hour", ready, f"{down} ready ~{6 + ready}:00 Mon", authority="PREDICTED")
        bb.post(self.name, "fields", self.fields)
        return down, ready
