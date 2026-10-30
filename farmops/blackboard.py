"""Shared plan state. Agents post constraints here instead of messaging each other down a chain."""
import time


class Blackboard:
    def __init__(self):
        self.constraints = {}      # key -> value, read by the solver
        self.options = []          # procurement/ops options the solver should evaluate
        self.log = []              # (agent, message)
        self.alerts = []           # watchdog escalations straight to the supervisor
        self.heartbeats = {}       # agent -> last beat time

    # OBSERVED | VERIFIED | INFERRED | PREDICTED | USER_ASSERTED | UNKNOWN
    def post(self, agent, key, value, note="", authority="OBSERVED"):
        self.constraints[key] = value
        self.authority = getattr(self, "authority", {})
        self.authority[key] = authority
        self.log.append((agent, f"{key} = {value}  [{authority}]" + (f"  ({note})" if note else "")))
        self.beat(agent)

    def say(self, agent, msg):
        self.log.append((agent, msg))
        self.beat(agent)

    def beat(self, agent):
        self.heartbeats[agent] = time.time()

    def alert(self, msg):
        self.alerts.append(msg)
