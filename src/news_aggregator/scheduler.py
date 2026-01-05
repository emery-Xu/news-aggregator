"""Scheduler for automated daily pipeline execution."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .orchestrator import PipelineOrchestrator
from .logger import get_logger


class Scheduler:
    """Manages scheduled execution of the news aggregation pipeline."""

    def __init__(self, pipeline: PipelineOrchestrator, run_time: str = "08:00"):
        """
        Initialize scheduler.

        Args:
            pipeline: Pipeline orchestrator instance
            run_time: Daily run time in HH:MM format (24-hour)
        """
        self.pipeline = pipeline
        self.run_time = run_time
        self.logger = get_logger()

        # Parse run time
        try:
            hours, minutes = run_time.split(':')
            self.hours = int(hours)
            self.minutes = int(minutes)
        except ValueError:
            raise ValueError(f"Invalid run_time format: {run_time}. Use HH:MM format.")

        # Create scheduler
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the scheduler (blocking)."""
        self.logger.info(f"Starting scheduler: pipeline will run daily at {self.run_time}")

        # Add job to scheduler
        trigger = CronTrigger(hour=self.hours, minute=self.minutes)
        self.scheduler.add_job(
            self._run_pipeline_wrapper,
            trigger=trigger,
            id='daily_news_pipeline',
            name='Daily News Aggregation Pipeline',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.logger.info("Scheduler started successfully")
        self.logger.info(f"Next run scheduled for: {self.run_time}")

        try:
            # Keep the scheduler running
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Received shutdown signal")
            self.stop()

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping scheduler")
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")

    async def run_once(self):
        """Execute the pipeline once immediately (for testing)."""
        self.logger.info("Running pipeline once (manual execution)")
        result = await self.pipeline.run_pipeline()
        return result

    async def _run_pipeline_wrapper(self):
        """Wrapper for scheduled pipeline execution."""
        try:
            await self.pipeline.run_pipeline()
        except Exception as e:
            self.logger.error(f"Scheduled pipeline execution failed: {e}", exc_info=True)
