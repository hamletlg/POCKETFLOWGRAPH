from .base import BasePlatformNode
from pocketflow import Node


class CronNode(BasePlatformNode, Node):
    NODE_TYPE = "cron"
    DESCRIPTION = "Run workflow on a schedule (Interval or Cron)"
    PARAMS = {
        "schedule_type": {
            "type": "string",
            "enum": ["Interval", "Cron"],
            "default": "Interval",
            "description": "Type of schedule",
        },
        "interval_value": {"type": "int", "description": "Interval value (e.g., 5)"},
        "interval_unit": {
            "type": "string",
            "enum": ["Seconds", "Minutes", "Hours"],
            "default": "Minutes",
            "description": "Interval unit",
        },
        "cron_expression": {
            "type": "string",
            "description": "Cron expression (e.g., '* * * * *')",
        },
    }

    def prep(self, shared):
        return shared

    def exec(self, prep_res):
        # The CronNode itself doesn't "execute" the schedule, the scheduler does.
        # When the flow runs, this node just acts as an entry point or pass-through.
        # We can log the successful trigger here.
        return "Cron Triggered"
