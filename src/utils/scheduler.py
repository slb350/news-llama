"""
Scheduler for automated news curation
"""
import asyncio
import schedule
import time
from typing import Callable, Awaitable
from datetime import datetime

from src.utils.logger import logger


class NewsScheduler:
    """Schedules automated news curation runs"""

    def __init__(self, config, curation_func: Callable[[], Awaitable[None]]):
        """
        Initialize scheduler

        Args:
            config: Application configuration
            curation_func: Async function to run for news curation
        """
        self.config = config
        self.curation_func = curation_func
        self.scheduler_config = config.scheduler

    def setup_schedule(self) -> None:
        """Setup the schedule based on configuration"""
        if not self.scheduler_config.enabled:
            logger.info("Scheduler is disabled")
            return

        frequency = self.scheduler_config.frequency.lower()
        schedule_time = self.scheduler_config.time

        # Clear any existing jobs
        schedule.clear()

        # Setup schedule based on frequency
        if frequency == "hourly":
            schedule.every().hour.do(self._run_async_job)
            logger.info("Scheduled: Running every hour")

        elif frequency == "daily":
            schedule.every().day.at(schedule_time).do(self._run_async_job)
            logger.info(f"Scheduled: Running daily at {schedule_time}")

        elif frequency == "weekly":
            # Default to Monday at specified time
            schedule.every().monday.at(schedule_time).do(self._run_async_job)
            logger.info(f"Scheduled: Running weekly (Mondays) at {schedule_time}")

        elif frequency.startswith("every_"):
            # Handle "every_X_minutes" or "every_X_hours"
            parts = frequency.split("_")
            if len(parts) == 3:
                interval = int(parts[1])
                unit = parts[2]

                if unit == "minutes":
                    schedule.every(interval).minutes.do(self._run_async_job)
                    logger.info(f"Scheduled: Running every {interval} minutes")
                elif unit == "hours":
                    schedule.every(interval).hours.do(self._run_async_job)
                    logger.info(f"Scheduled: Running every {interval} hours")
                else:
                    logger.warning(f"Unknown schedule unit: {unit}")
            else:
                logger.warning(f"Invalid schedule frequency format: {frequency}")
        else:
            logger.warning(f"Unknown schedule frequency: {frequency}")

    def _run_async_job(self) -> None:
        """Wrapper to run async curation function in sync context"""
        logger.info(f"Scheduled run starting at {datetime.now()}")
        try:
            asyncio.run(self.curation_func())
            logger.info("Scheduled run completed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled run: {e}")

    def run_forever(self) -> None:
        """Run the scheduler indefinitely"""
        if not self.scheduler_config.enabled:
            logger.info("Scheduler is disabled, not running")
            return

        logger.info("Starting scheduler loop...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise

    def run_once_then_schedule(self) -> None:
        """Run immediately once, then start the schedule"""
        if not self.scheduler_config.enabled:
            logger.info("Scheduler is disabled")
            return

        # Run immediately
        logger.info("Running initial curation before starting scheduler...")
        self._run_async_job()

        # Setup and run schedule
        self.setup_schedule()
        self.run_forever()
