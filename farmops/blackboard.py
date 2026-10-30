"""Shared plan state. Agents post constraints here instead of messaging each other down a chain."""
import time


class Blackboard:
    def __init__(self):
        self.constraints = {}      # key -> value, read by the solver
        self.options = []          # procurement/ops options the solver should evaluate
        self.log = []              # (agent, message)
        self.alerts = []           # watchdog escalations straight to the supervisor
        self.heartbeats = {}       # agent -> last beat time

    def post(self, agent, key, value, note=""):
        self.constraints[key] = value
        self.log.append((agent, f"{key} = {value}" + (f"  ({note})" if note else "")))
        self.beat(agent)

    def say(self, agent, msg):
        self.log.append((agent, msg))
        self.beat(agent)

    def beat(self, agent):
        self.heartbeats[agent] = time.time()

    def alert(self, msg):
        self.alerts.append(msg)
