import os
import json
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from .engine import run_workflow

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, workflows_dir: str):
        self.scheduler = AsyncIOScheduler()
        self.workflows_dir = workflows_dir
        self.jobs = {}

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")
        self.refresh_jobs()

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def refresh_jobs(self):
        """Scans all workflows and schedules them if they have a CronNode"""
        logger.info("Refreshing scheduled jobs...")
        self.scheduler.remove_all_jobs()
        
        if not os.path.exists(self.workflows_dir):
            return

        for filename in os.listdir(self.workflows_dir):
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(self.workflows_dir, filename)
                    with open(filepath, "r") as f:
                        workflow = json.load(f)
                    
                    self._schedule_workflow(filename, workflow)
                except Exception as e:
                    logger.error(f"Failed to load workflow {filename}: {e}")

    def _schedule_workflow(self, filename: str, workflow: dict):
        nodes = workflow.get("nodes", [])
        cron_node = next((n for n in nodes if n.get("type") == "cron"), None)
        
        if not cron_node:
            return

        name = filename.replace(".json", "")
        config = cron_node.get("data", {})
        
        schedule_type = config.get("schedule_type", "Interval")
        
        trigger = None
        
        try:
            if schedule_type == "Cron":
                expr = config.get("cron_expression", "* * * * *")
                if not expr: return
                trigger = CronTrigger.from_crontab(expr)
            else: # Interval
                val = int(config.get("interval_value", 1))
                unit = config.get("interval_unit", "Minutes")
                
                if unit == "Seconds":
                    trigger = IntervalTrigger(seconds=val)
                elif unit == "Hours":
                    trigger = IntervalTrigger(hours=val)
                else:
                    trigger = IntervalTrigger(minutes=val)
            
            if trigger:
                self.scheduler.add_job(
                    self.execute_job,
                    trigger,
                    args=[name, workflow],
                    id=name,
                    replace_existing=True
                )
                logger.info(f"Scheduled workflow '{name}' with {trigger}")
                
        except Exception as e:
            logger.error(f"Failed to schedule workflow {name}: {e}")

    async def execute_job(self, name: str, workflow: dict):
        logger.info(f"Executing scheduled workflow: {name}")
        try:
            # We construct the workflow object expected by engine.run_workflow
            # The JSON saved structure is slightly different from what run_workflow expects? 
            # Let's check engine.py or how main.py calls it.
            # main.py passes `Workflow` pydantic model. 
            # We can pass the dict if we convert it or if engine accepts dict.
            # Let's check engine.py first.
            # Assuming main.py initializes engine and runs it.
            # We need to import run_workflow from engine.
            
            result = await run_workflow(workflow)
            logger.info(f"Workflow '{name}' finished. Result: {result}")
        except Exception as e:
            logger.error(f"Workflow '{name}' execution failed: {e}")
