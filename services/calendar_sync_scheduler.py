#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calendar Sync Scheduler
Handles automatic periodic synchronization of committee meetings and events to calendar
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')


class CalendarSyncScheduler:
    """Background scheduler for automatic calendar synchronization"""

    def __init__(self, calendar_service, db_manager, audit_logger=None):
        """
        Initialize Calendar Sync Scheduler

        Args:
            calendar_service: CalendarService instance
            db_manager: DatabaseManager instance
            audit_logger: AuditLogger instance (optional)
        """
        self.calendar_service = calendar_service
        self.db = db_manager
        self.audit_logger = audit_logger
        self.scheduler = None
        self.is_running = False

        logger.info("Calendar sync scheduler initialized")

    def start(self):
        """Start the background scheduler"""
        if self.scheduler and self.is_running:
            logger.warning("Scheduler is already running")
            return

        try:
            # Get sync interval from settings
            interval_hours = int(self.db.get_system_setting('calendar_sync_interval_hours') or '1')
            sync_enabled = self.db.get_system_setting('calendar_sync_enabled') == '1'

            if not sync_enabled:
                logger.info("Calendar sync is disabled in settings - scheduler not started")
                return

            # Create scheduler
            self.scheduler = BackgroundScheduler(timezone=ISRAEL_TZ)

            # Add job to run every N hours
            self.scheduler.add_job(
                func=self._sync_job,
                trigger=IntervalTrigger(hours=interval_hours),
                id='calendar_sync',
                name='Calendar Sync Job',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )

            # Start scheduler
            self.scheduler.start()
            self.is_running = True

            logger.info(f"Calendar sync scheduler started - running every {interval_hours} hour(s)")

            # Run initial sync after a short delay to ensure Azure AD credentials are loaded
            # Use scheduler to run initial sync after 5 seconds instead of immediately
            logger.info("Scheduling initial calendar sync in 5 seconds...")
            self.scheduler.add_job(
                func=self._sync_job,
                trigger=DateTrigger(run_date=datetime.now(ISRAEL_TZ) + timedelta(seconds=5)),
                id='initial_calendar_sync',
                replace_existing=True
            )

        except Exception as e:
            logger.error(f"Error starting calendar sync scheduler: {e}", exc_info=True)
            self.is_running = False

    def stop(self):
        """Stop the background scheduler"""
        if not self.scheduler or not self.is_running:
            logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Calendar sync scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    def _sync_job(self):
        """
        Background sync job
        Called by scheduler at regular intervals
        """
        try:
            logger.info("=== Starting scheduled calendar sync ===")
            start_time = datetime.now(ISRAEL_TZ)

            # Perform full sync
            result = self.calendar_service.sync_all()

            end_time = datetime.now(ISRAEL_TZ)
            duration = (end_time - start_time).total_seconds()

            # Log results
            if result['success']:
                logger.info(
                    f"Calendar sync completed successfully in {duration:.2f}s - "
                    f"Committees: {result['committees_synced']}, "
                    f"Events: {result['events_synced']}, "
                    f"Failures: {result['failures']}"
                )

                # Log to audit if available (direct DB call since no request context)
                if self.db:
                    try:
                        self.db.add_audit_log(
                            user_id=None,
                            username='system',
                            action='calendar_sync',
                            entity_type='calendar',
                            entity_id=None,
                            entity_name='automatic_sync',
                            details=f"Synced {result['committees_synced']} committees and {result['events_synced']} events",
                            ip_address='127.0.0.1',
                            user_agent='calendar_sync_scheduler',
                            status='success',
                            error_message=None
                        )
                    except Exception as log_error:
                        logger.warning(f"Failed to write audit log: {log_error}")
            else:
                logger.error(f"Calendar sync failed: {result['message']}")

                # Log failure to audit (direct DB call since no request context)
                if self.db:
                    try:
                        self.db.add_audit_log(
                            user_id=None,
                            username='system',
                            action='calendar_sync',
                            entity_type='calendar',
                            entity_id=None,
                            entity_name='automatic_sync',
                            details=f"Sync failed after processing {result['committees_synced']} committees and {result['events_synced']} events",
                            ip_address='127.0.0.1',
                            user_agent='calendar_sync_scheduler',
                            status='error',
                            error_message=result['message']
                        )
                    except Exception as log_error:
                        logger.warning(f"Failed to write audit log: {log_error}")

            logger.info("=== Calendar sync job complete ===")

        except Exception as e:
            logger.error(f"Error in calendar sync job: {e}", exc_info=True)

            # Log error to audit (direct DB call since no request context)
            if self.db:
                try:
                    self.db.add_audit_log(
                        user_id=None,
                        username='system',
                        action='calendar_sync',
                        entity_type='calendar',
                        entity_id=None,
                        entity_name='automatic_sync',
                        details='Calendar sync job failed with exception',
                        ip_address='127.0.0.1',
                        user_agent='calendar_sync_scheduler',
                        status='error',
                        error_message=str(e)
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to write audit log: {log_error}")

    def trigger_sync_now(self):
        """Manually trigger a sync job immediately"""
        logger.info("Manual calendar sync triggered")
        self._sync_job()

    def get_next_run_time(self):
        """Get the next scheduled run time"""
        if not self.scheduler or not self.is_running:
            return None

        try:
            job = self.scheduler.get_job('calendar_sync')
            if job:
                return job.next_run_time
            return None
        except Exception as e:
            logger.error(f"Error getting next run time: {e}")
            return None

    def is_scheduler_running(self) -> bool:
        """Check if scheduler is running"""
        return self.is_running
