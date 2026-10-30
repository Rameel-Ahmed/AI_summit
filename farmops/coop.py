"""Multi-farm co-op: farms share scarce resources without sharing private data.

Each farm runs its own agents + solver locally. For each pooled resource, a farm computes
its *marginal value* (grain + cost saved if it gets the resource) with its own solver and
broadcasts only that bid. Farms agree on the winner by max-consensus gossip over a ring
network (no central broker). Fields, yields, finances and machine health never leave the farm.

    python -m farmops.coop
"""
from . import solver
from .main import build_blackboard

FARMS = {
    "Farm A": {"order": "Combine 2 is throwing HYD-217, rain hits Thursday, elevator in Lafayette is backed up.",
               "fields": {"North 150": 150, "Creek 200": 200, "Home 120": 120, "West 180": 180}},
    "Farm B": {"order": "Both combines running, rain Thursday, elevator is backed up.",
               "fields": {"River 260": 260, "Ridge 240": 240, "South 200": 200, "Barn 150": 150}},
    "Farm C": {"order": "Combine 1 shows ENG-102, rain Thursday.",
               "fields": {"East 140": 140, "Pond 100": 100, "Lane 120": 120}},
}

# Capacity farms or vendors published into the co-op pool (illustrative)
POOL = [
    {"id": "Extra elevator slot", "kind": "storage", "bu_per_day": 8000, "price": 600},
    {"id": "Second elevator slot", "kind": "storage", "bu_per_day": 8000, "price": 600},
    {"id": "Co-op combine", "kind": "combine", "rate": 9, "from_day": "Tue", "price": 2400},
]


def local_cost(bb, won):
    """Private to the farm: best plan cost (grain at risk + spend) given resources won so far."""
    combine = next((r for r in won if r["kind"] == "combine"), None)
    storage = sum(r["bu_per_day"] for r in won if r["kind"] == "storage")
    plan = solver.solve(bb, "local", overtime=True, extra_combine=combine, extra_storage_bu=storage)
    if plan["status"] not in ("OPTIMAL", "FEASIBLE"):
        return float("inf"), plan
    return plan["grain_at_risk"] + plan["extra_cost"], plan


def max_consensus(bids, rounds=None):
    """Gossip on a ring: each farm repeatedly adopts the best (bid, farm) it hears from neighbors."""
    names = list(bids)
    belief = {n: (bids[n], n) for n in names}
    rounds = rounds or len(names) - 1
    for r in range(1, rounds + 1):
        new = {}
        for i, n in enumerate(names):
            nbrs = [names[(i - 1) % len(names)], names[(i + 1) % len(names)]]
            new[n] = max([belief[n]] + [belief[m] for m in nbrs])
        belief = new
        print(f"    gossip round {r}: " + ", ".join(f"{n} thinks {b[1]} ({b[0]:,})" for n, b in belief.items()))
    winners = {b[1] for b in belief.values()}
    assert len(winners) == 1, "consensus not reached"
    return belief[names[0]]


def run():
    farms = {}
    print("\nCO-OP: each farm builds its plan locally (private data stays on the farm)\n")
    for name, cfg in FARMS.items():
        bb, agents = build_blackboard(cfg["order"], cfg["fields"])
        farms[name] = {"bb": bb, "won": [], "agents": agents}
        cost, plan = local_cost(bb, [])
        farms[name]["cost"] = cost
        print(f"  {name}: {plan['acres_at_risk']} acres at risk before rain (local plan, not shared)")

    for res in POOL:
        print(f"\nAUCTION: {res['id']} (price ${res['price']:,})")
        bids = {}
        for name, f in farms.items():
            new_cost, _ = local_cost(f["bb"], f["won"] + [res])
            value = int(f["cost"] - new_cost - res["price"])
            bids[name] = max(0, value)
            print(f"  {name} broadcasts bid: ${bids[name]:,}  (only this number leaves the farm)")
        best_bid, winner = max_consensus(bids)
        if best_bid <= 0:
            print("  No farm gains enough to justify the price. Resource stays unassigned.")
            continue
        print(f"  CONSENSUS: {winner} gets {res['id']} (net value ${best_bid:,}). "
              f"Pending {winner} supervisor approval.")
        f = farms[winner]
        f["won"].append(res)
        f["cost"], _ = local_cost(f["bb"], f["won"])

    print("\nRESULT")
    for name, f in farms.items():
        _, plan = local_cost(f["bb"], f["won"])
        got = ", ".join(r["id"] for r in f["won"]) or "nothing from pool"
        spend = plan["extra_cost"] + sum(r["price"] for r in f["won"])
        print(f"  {name}: {got}; {plan['acres_at_risk']} acres at risk, extra spend ${spend:,}")


if __name__ == "__main__":
    run()
