"""Run the single-farm demo.

    python -m farmops.main
    python -m farmops.main "Combine 2 is throwing HYD-217, rain Thursday, elevator is backed up"
    python -m farmops.main --auto      # skip the approval prompt
"""
import sys

from . import llm
from . import solver
from .agents import Admin, Diagnostics, Logistics, Ops, Procurement, Technician
from .blackboard import Blackboard

DEFAULT_ORDER = ("Combine 2 is throwing a hydraulic code, rain hits Thursday, "
                 "and the elevator in Lafayette is backed up. Get Creek 200 done first.")


def build_blackboard(order, fields=None):
    """Single-farm pipeline: neural in, then every specialist posts constraints."""
    bb = Blackboard()
    agents = Admin(), Diagnostics(), Technician(), Procurement(), Logistics(), Ops(fields)
    admin, diag, tech, proc, logi, ops = agents
    facts = admin.handle_order(bb, order)
    diag.inspect(bb, facts)
    tech.plan_repair(bb)
    proc.source(bb)
    logi.capacity(bb)
    ops.availability(bb)
    return bb, agents


def run(order, auto=False):
    print(f"\nSUPERVISOR: \"{order}\"\n")
    bb, (admin, diag, tech, proc, logi, ops) = build_blackboard(order)

    print("AGENT LOG")
    for agent, msg in bb.log:
        print(f"  [{agent:<11}] {msg}")

    # Symbolic core: evaluate options
    results = [
        solver.solve(bb, "A: Repair, normal hours"),
        solver.solve(bb, "B: Repair + overtime", overtime=True),
        solver.solve(bb, "C: Repair + rent a combine", rent=True),
    ]
    diag.watch(bb, [a.name for a in (admin, diag, tech, proc, logi, ops)], results)

    if bb.alerts:
        print("\nDIRECT TO SUPERVISOR (watchdog)")
        for a in bb.alerts:
            print(f"  ! {a}")

    ok = [r for r in results if r["status"] in ("OPTIMAL", "FEASIBLE")]
    ok.sort(key=lambda r: r["grain_at_risk"] + r["extra_cost"])

    print("\nOPTIONS (ranked by grain at risk + extra cost)")
    for i, r in enumerate(ok, 1):
        flag = "  [OVER BUDGET]" if r["over_budget"] else ""
        print(f"  {i}. {llm.explain(r, 'supervisor')}{flag}")

    if not ok:
        print("  No feasible plan. Escalating to supervisor.")
        return

    if auto:
        choice = 1
    else:
        raw = input(f"\nApprove which option? [1-{len(ok)}, enter = 1, q = reject all]: ").strip()
        if raw.lower() == "q":
            print("Rejected. Nothing dispatched.")
            return
        choice = int(raw) if raw.isdigit() and 1 <= int(raw) <= len(ok) else 1

    plan = ok[choice - 1]
    print(f"\nAPPROVED: {plan['name']}\n\nSCHEDULE")
    for day, combines in plan["schedule"].items():
        for k, fields in combines.items():
            if fields:
                print(f"  {day}  {k:<10} " + ", ".join(f"{f} {hrs}h" for f, hrs in fields.items()))

    c = bb.constraints
    print("\nDISPATCH")
    if c.get("tech_assigned"):
        print(f"  -> {c['tech_assigned']} (tech): fix {c['down_machine']} ({c['part_needed']}), "
              f"part arrives in ~{c['part_eta_hours']}h. Lockout/tagout first.")
    print(f"  -> Drivers: max {c['haul_bu_per_day']:,} bu/day across trucks, HOS 11h cap enforced.")
    print("  -> Operators: follow schedule above; no shift over 14h.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--auto"]
    run(" ".join(args) if args else DEFAULT_ORDER, auto="--auto" in sys.argv)
