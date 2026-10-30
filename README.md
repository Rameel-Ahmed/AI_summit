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
- `farmops/main.py` demo entry point

## Next
- Multi-farm layer: consensus-based auction (CBBA) for shared elevator slots, rental combines and crews,
  without farms sharing private data.
