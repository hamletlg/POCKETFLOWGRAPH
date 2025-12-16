from .base import BasePlatformNode
from pocketflow import Node

class CronNode(BasePlatformNode, Node):
    NODE_TYPE = "cron"
    DESCRIPTION = "Run workflow on a schedule (Interval or Cron)"
    PARAMS = {
        "schedule_type": "string", # "Interval" or "Cron"
        "interval_value": "int",   # e.g. 5
        "interval_unit": "string", # "Seconds", "Minutes", "Hours"
        "cron_expression": "string" # e.g. "* * * * *"
    }

    def prep(self, shared):
        return shared

    def exec(self, prep_res):
        # The CronNode itself doesn't "execute" the schedule, the scheduler does.
        # When the flow runs, this node just acts as an entry point or pass-through.
        # We can log the successful trigger here.
        return "Cron Triggered"
