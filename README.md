# FarmOps: neurosymbolic multi-agent harvest planner

Purdue x Google AI Summit, Student Innovation Sprint (Option 1: Smarter Operations).

A supervisor gives a spoken/typed order. Specialist agents turn it into constraints, a CP-SAT solver
finds plans that are guaranteed feasible under legal, physical and human limits, and the supervisor approves one.

```
            SUPERVISOR (human)  <-- direct safety line --  DIAGNOSTICS (watchdog)
                 |  order / approval                          monitors machines + agent heartbeats
               ADMIN  (neural in: order -> facts, neural out: plan -> plain language)
                 |
          BLACKBOARD + CP-SAT SOLVER  (shared plan state, single source of truth)
         /        |          |         \
       OPS   PROCUREMENT  LOGISTICS  TECHNICIAN
```

## Constraints modeled
- **Legal:** truck driver hours-of-service (11 h/day)
- **Physical:** combine throughput, elevator intake, on-farm dryer capacity, rain deadline
- **Human:** operator fatigue cap (12 h normal, 14 h hard ceiling), technician certifications
- **Business:** parts lead time and cost, rental cost, supervisor budget

## Run
```bash
pip install -r requirements.txt
python -m farmops.main                       # default scenario, asks you to approve
python -m farmops.main --auto "Combine 2 shows ENG-102, rain Wednesday, keep spend under \$500"
```
Set `GEMINI_API_KEY` to use Gemini for order parsing and explanations. Without it, a keyword
fallback runs so the demo works offline.

## Layout
- `farmops/scenario.py` farm data (illustrative numbers)
- `farmops/agents.py` Admin, Diagnostics (watchdog), Technician, Procurement, Logistics, Ops
- `farmops/blackboard.py` shared state agents post constraints to
- `farmops/solver.py` CP-SAT model, evaluates options A/B/C
- `farmops/llm.py` Gemini parse + explain, with offline fallback
- `farmops/main.py` single-farm demo
- `farmops/coop.py` multi-farm co-op auction with max-consensus

## Authority tags
Every claim an agent posts carries a tag: OBSERVED, VERIFIED, INFERRED, PREDICTED, USER_ASSERTED or UNKNOWN.
The solver uses predictions and inferences, but the log shows the supervisor which facts are guesses.

## Multi-farm co-op (`python -m farmops.coop`)
Farms pool scarce resources (elevator slots, a co-op combine). Each farm runs its own agents and solver
locally, computes its marginal value for a resource, and broadcasts **only its bid**. Farms agree on the
winner by max-consensus gossip over a ring network, with no central broker. Fields, yields and machine
health never leave the farm. A resource nobody gains from stays unassigned. The winning farm's supervisor
still approves. This is a sequential auction inspired by CBBA, not a full CBBA implementation.

## Next
- Weather agent on NWS forecasts (rain as a probabilistic penalty, not a hard deadline)
- Priority re-weighting from the supervisor ("protect crop over cost") and instant re-solve
- Data freshness (`valid_until`) checks in the watchdog
