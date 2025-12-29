#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calendar Sync Service
Handles synchronization of committee meetings and event deadlines to Microsoft 365 shared calendar
Uses Microsoft Graph API with app-only authentication
"""

import requests
import logging
import hashlib
import json
import threading
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ISRAEL_TZ = ZoneInfo('Asia/Jerusalem')


class CalendarService:
    """Microsoft 365 Calendar Synchronization Service"""

    def __init__(self, ad_service, db_manager):
        """
        Initialize Calendar Service

        Args:
            ad_service: ADService instance for authentication
            db_manager: DatabaseManager instance for storing sync state
        """
        self.ad_service = ad_service
        self.db = db_manager
        self.graph_endpoint = 'https://graph.microsoft.com/v1.0'

        # Thread lock to prevent concurrent sync/reset operations
        self._sync_lock = threading.Lock()

        # Get calendar settings from database
        self.calendar_email = self.db.get_system_setting('calendar_sync_email') or 'plan@innovationisrael.org.il'
        self.sync_enabled = self.db.get_system_setting('calendar_sync_enabled') == '1'

        logger.info(f"Calendar service initialized - Email: {self.calendar_email}, Enabled: {self.sync_enabled}")

    def is_enabled(self) -> bool:
        """Check if calendar sync is enabled"""
        return self.sync_enabled

    def _get_access_token(self) -> Optional[str]:
        """
        Get app-only access token for calendar operations

        Returns:
            Access token or None on error
        """
        return self.ad_service.get_app_only_token()

    def _get_headers(self, access_token: str) -> Dict:
        """Get HTTP headers for Graph API requests"""
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Prefer': 'outlook.timezone="Asia/Jerusalem"'
        }

    def create_calendar_event(self, subject: str, start_date: date, end_date: date = None,
                             body: str = "", location: str = "", is_all_day: bool = True,
                             user_email: str = None, start_time: str = None, end_time: str = None) -> Tuple[bool, Optional[str], str]:
        """
        Create a calendar event in the shared calendar

        Args:
            subject: Event title/subject
            start_date: Event start date
            end_date: Event end date (defaults to start_date)
            body: Event description (HTML supported)
            location: Event location
            is_all_day: Whether this is an all-day event
            user_email: Target calendar user email (defaults to self.calendar_email)
            start_time: Start time in HH:MM format (e.g., "09:00"), only used if is_all_day=False
            end_time: End time in HH:MM format (e.g., "15:00"), only used if is_all_day=False

        Returns:
            Tuple of (success, event_id, message)
        """
        if not self.is_enabled():
            return False, None, "Calendar sync is disabled"

        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, None, "Failed to acquire access token"

            if end_date is None:
                end_date = start_date

            target_email = user_email or self.calendar_email

            # Build start and end datetime based on whether it's an all-day event
            if is_all_day:
                # For all-day events, Microsoft Graph requires duration of at least 24 hours.
                # Ensure end_date is at least start_date + 1 day for single-day all-day events.
                if end_date <= start_date:
                    end_date = start_date + timedelta(days=1)

                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.min.time())
            else:
                # For timed events, parse the time strings
                if start_time:
                    start_hour, start_minute = map(int, start_time.split(':'))
                    start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
                else:
                    # Default to 09:00 if no time specified
                    start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0))

                if end_time:
                    end_hour, end_minute = map(int, end_time.split(':'))
                    end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
                else:
                    # Default to 15:00 if no time specified
                    end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=15, minute=0))

            # Build event object
            event = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "start": {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                },
                "end": {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                },
                "isAllDay": is_all_day,
                "location": {
                    "displayName": location
                }
            }

            # Create event in user's calendar
            url = f"{self.graph_endpoint}/users/{target_email}/calendar/events"
            headers = self._get_headers(access_token)

            logger.info(f"Creating calendar event: {subject} on {start_date}")
            response = requests.post(url, json=event, headers=headers)

            if response.status_code == 201:
                event_data = response.json()
                event_id = event_data.get('id')
                logger.info(f"Successfully created calendar event with ID: {event_id}")
                return True, event_id, "Event created successfully"
            else:
                error_msg = f"Graph API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, None, error_msg

        except Exception as e:
            logger.error(f"Error creating calendar event: {e}", exc_info=True)
            return False, None, str(e)

    def update_calendar_event(self, event_id: str, subject: str = None, start_date: date = None,
                              end_date: date = None, body: str = None, location: str = None,
                              is_all_day: bool = True, user_email: str = None, start_time: str = None,
                              end_time: str = None) -> Tuple[bool, str]:
        """
        Update an existing calendar event

        Args:
            event_id: Calendar event ID to update
            subject: New event title (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)
            body: New description (optional)
            location: New location (optional)
            is_all_day: Whether this is an all-day event
            user_email: Target calendar user email (defaults to self.calendar_email)
            start_time: Start time in HH:MM format (e.g., "09:00"), only used if is_all_day=False
            end_time: End time in HH:MM format (e.g., "15:00"), only used if is_all_day=False

        Returns:
            Tuple of (success, message)
        """
        if not self.is_enabled():
            return False, "Calendar sync is disabled"

        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, "Failed to acquire access token"

            target_email = user_email or self.calendar_email

            # Build update object (only include fields that are provided)
            event_update = {}

            if subject is not None:
                event_update["subject"] = subject

            if body is not None:
                event_update["body"] = {
                    "contentType": "HTML",
                    "content": body
                }

            if start_date is not None:
                effective_end_date = end_date if end_date is not None else start_date

                # Build start and end datetime based on whether it's an all-day event
                if is_all_day:
                    # For all-day events, ensure at least 24 hours duration by default
                    if effective_end_date <= start_date:
                        effective_end_date = start_date + timedelta(days=1)

                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    end_datetime = datetime.combine(effective_end_date, datetime.min.time())
                else:
                    # For timed events, parse the time strings
                    if start_time:
                        start_hour, start_minute = map(int, start_time.split(':'))
                        start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=start_hour, minute=start_minute))
                    else:
                        # Default to 09:00 if no time specified
                        start_datetime = datetime.combine(start_date, datetime.min.time().replace(hour=9, minute=0))

                    if end_time:
                        end_hour, end_minute = map(int, end_time.split(':'))
                        end_datetime = datetime.combine(effective_end_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
                    else:
                        # Default to 15:00 if no time specified
                        end_datetime = datetime.combine(effective_end_date, datetime.min.time().replace(hour=15, minute=0))

                event_update["start"] = {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                }
                event_update["end"] = {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                }
                event_update["isAllDay"] = is_all_day

            # If only end_date is provided (rare), update it directly
            elif end_date is not None:
                if is_all_day:
                    end_datetime = datetime.combine(end_date, datetime.min.time())
                else:
                    if end_time:
                        end_hour, end_minute = map(int, end_time.split(':'))
                        end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=end_hour, minute=end_minute))
                    else:
                        end_datetime = datetime.combine(end_date, datetime.min.time().replace(hour=15, minute=0))

                event_update["end"] = {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                }

            if location is not None:
                event_update["location"] = {
                    "displayName": location
                }

            # Update event
            url = f"{self.graph_endpoint}/users/{target_email}/calendar/events/{event_id}"
            headers = self._get_headers(access_token)

            logger.info(f"Updating calendar event ID: {event_id}")
            response = requests.patch(url, json=event_update, headers=headers)

            if response.status_code == 200:
                logger.info(f"Successfully updated calendar event: {event_id}")
                return True, "Event updated successfully"
            else:
                error_msg = f"Graph API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            logger.error(f"Error updating calendar event: {e}", exc_info=True)
            return False, str(e)

    def delete_calendar_event(self, event_id: str, user_email: str = None) -> Tuple[bool, str]:
        """
        Delete a calendar event

        Args:
            event_id: Calendar event ID to delete
            user_email: Target calendar user email (defaults to self.calendar_email)

        Returns:
            Tuple of (success, message)
        """
        if not self.is_enabled():
            return False, "Calendar sync is disabled"

        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, "Failed to acquire access token"

            target_email = user_email or self.calendar_email

            # Delete event
            url = f"{self.graph_endpoint}/users/{target_email}/calendar/events/{event_id}"
            headers = self._get_headers(access_token)

            logger.info(f"Deleting calendar event ID: {event_id}")
            response = requests.delete(url, headers=headers)

            if response.status_code == 204:
                logger.info(f"Successfully deleted calendar event: {event_id}")
                return True, "Event deleted successfully"
            elif response.status_code == 404:
                logger.warning(f"Calendar event not found (already deleted?): {event_id}")
                return True, "Event not found (may already be deleted)"
            else:
                error_msg = f"Graph API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}", exc_info=True)
            return False, str(e)

    def sync_committee_to_calendar(self, vaadot_id: int) -> Tuple[bool, str]:
        """
        Sync a committee meeting to calendar

        Args:
            vaadot_id: Committee ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get committee details
            committee = self.db.get_vaada_by_id(vaadot_id)
            if not committee:
                return False, f"Committee {vaadot_id} not found"

            # Check if committee is deleted or cancelled
            if committee.get('is_deleted') == 1 or committee.get('status') == 'cancelled':
                # Mark for deletion
                sync_records = self.db.mark_calendar_sync_deleted('vaadot', vaadot_id, self.calendar_email)
                for record in sync_records:
                    if record['calendar_event_id']:
                        self.delete_calendar_event(record['calendar_event_id'])
                return True, "Committee marked for deletion"

            # Get committee type and division names
            committee_type_name = committee.get('committee_type_name', 'ועדה')
            hativa_name = committee.get('hativa_name', '')
            vaada_date = committee.get('vaada_date')
            notes = committee.get('notes', '')
            is_operational = committee.get('is_operational', 0)
            status = committee.get('status', '')
            start_time = committee.get('start_time')
            end_time = committee.get('end_time')

            if not vaada_date:
                return False, "Committee has no date"

            # Parse date
            if isinstance(vaada_date, str):
                vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

            # Determine if this should be an all-day event or timed event
            is_all_day = not (start_time and end_time)

            # Build event title and description
            subject = f"{committee_type_name} - {hativa_name}"

            # Build HTML description with all details
            body_parts = [
                f"<h3>פרטי ועדה</h3>",
                f"<p><strong>סוג ועדה:</strong> {committee_type_name}</p>",
                f"<p><strong>חטיבה:</strong> {hativa_name}</p>",
                f"<p><strong>תאריך:</strong> {vaada_date.strftime('%d/%m/%Y')}</p>",
            ]

            # Add time information if available
            if start_time and end_time:
                body_parts.append(f"<p><strong>שעת התחלה:</strong> {start_time}</p>")
                body_parts.append(f"<p><strong>שעת סיום:</strong> {end_time}</p>")

            body_parts.append(f"<p><strong>סטטוס:</strong> {status}</p>")

            if is_operational:
                body_parts.append("<p><strong>ועדה תפעולית</strong></p>")

            if notes:
                body_parts.append(f"<p><strong>הערות:</strong> {notes}</p>")

            body = "\n".join(body_parts)

            # Calculate content hash to check if anything changed
            content_data = {
                'subject': subject,
                'start_date': str(vaada_date),
                'start_time': start_time,
                'end_time': end_time,
                'body': body
            }
            content_hash = hashlib.md5(json.dumps(content_data, sort_keys=True).encode('utf-8')).hexdigest()

            # Check if sync record exists
            sync_record = self.db.get_calendar_sync_record('vaadot', vaadot_id, None, self.calendar_email)

            if sync_record and sync_record.get('calendar_event_id'):
                # Check if content changed by comparing hash
                stored_hash = sync_record.get('content_hash')
                if stored_hash == content_hash and sync_record.get('sync_status') == 'synced':
                    # Content hasn't changed, skip update
                    return True, "Committee already synced (no changes)"
                
                # Update existing event (content changed or status is pending/failed)
                calendar_event_id = sync_record['calendar_event_id']
                success, message = self.update_calendar_event(
                    event_id=calendar_event_id,
                    subject=subject,
                    start_date=vaada_date,
                    body=body,
                    is_all_day=is_all_day,
                    start_time=start_time,
                    end_time=end_time
                )

                if success:
                    self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', calendar_event_id, content_hash=content_hash)
                    return True, f"Committee updated in calendar"
                else:
                    # If update fails with 404 (event not found), clear the calendar_event_id
                    # so next sync will create a new event instead of trying to update non-existent one
                    if 'ErrorItemNotFound' in message or '404' in message:
                        logger.info(f"Calendar event {calendar_event_id} no longer exists, clearing for recreation")
                        self.db.update_calendar_sync_status(sync_record['sync_id'], 'pending', None, error_message=message)
                        # Try to create a new event immediately
                        success2, new_event_id, create_msg = self.create_calendar_event(
                            subject=subject,
                            start_date=vaada_date,
                            body=body,
                            is_all_day=is_all_day,
                            start_time=start_time,
                            end_time=end_time
                        )
                        if success2:
                            self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', new_event_id, content_hash=content_hash)
                            return True, f"Committee recreated in calendar with ID: {new_event_id}"
                        else:
                            self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=create_msg)
                            return False, create_msg
                    else:
                        # For other errors, keep the existing calendar_event_id but mark as failed
                        self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', calendar_event_id, error_message=message)
                        return False, message
            else:
                # Create new event (no sync record or no calendar_event_id)
                success, event_id, message = self.create_calendar_event(
                    subject=subject,
                    start_date=vaada_date,
                    body=body,
                    is_all_day=is_all_day,
                    start_time=start_time,
                    end_time=end_time
                )

                if success:
                    # Create or update sync record
                    if sync_record:
                        # Update existing sync record with new event ID
                        self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', event_id, content_hash=content_hash)
                    else:
                        # Create new sync record
                        sync_id = self.db.create_calendar_sync_record('vaadot', vaadot_id, None, self.calendar_email, event_id)
                        self.db.update_calendar_sync_status(sync_id, 'synced', event_id, content_hash=content_hash)
                    return True, f"Committee created in calendar with ID: {event_id}"
                else:
                    if sync_record:
                        self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=message)
                    else:
                        sync_id = self.db.create_calendar_sync_record('vaadot', vaadot_id, None, self.calendar_email)
                        self.db.update_calendar_sync_status(sync_id, 'failed', error_message=message)
                    return False, message

        except Exception as e:
            logger.error(f"Error syncing committee {vaadot_id}: {e}", exc_info=True)
            return False, str(e)

    def sync_event_deadlines_to_calendar(self, event_id: int) -> Tuple[bool, str]:
        """
        Sync event deadlines to calendar

        Args:
            event_id: Event ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get event details
            event = self.db.get_event_by_id(event_id)
            if not event:
                return False, f"Event {event_id} not found"

            # Check if event is deleted or cancelled
            if event.get('is_deleted') == 1 or event.get('status') == 'cancelled':
                # Mark all deadlines for deletion
                sync_records = self.db.mark_calendar_sync_deleted('event_deadline', event_id, self.calendar_email)
                for record in sync_records:
                    if record['calendar_event_id']:
                        self.delete_calendar_event(record['calendar_event_id'])
                return True, "Event deadlines marked for deletion"

            event_name = event.get('name', '')
            event_type = event.get('event_type', '')
            expected_requests = event.get('expected_requests', 0)
            actual_submissions = event.get('actual_submissions', 0)
            committee_type_name = event.get('committee_type_name', '')
            hativa_name = event.get('hativa_name', '')

            # Deadline fields to sync
            deadline_fields = {
                'call_publication_date': 'פרסום קול קורא',
                'call_deadline_date': 'מועד אחרון להגשת בקשות',
                'intake_deadline_date': 'מועד אחרון לקליטה',
                'review_deadline_date': 'מועד אחרון לסיום בחינה',
                'response_deadline_date': 'מועד אחרון למתן תשובות'
            }

            synced_count = 0
            failed_count = 0
            processed_count = 0

            for field_name, hebrew_name in deadline_fields.items():
                deadline_date = event.get(field_name)

                if not deadline_date:
                    continue  # Skip if deadline not set

                # Parse date
                if isinstance(deadline_date, str):
                    deadline_date = datetime.strptime(deadline_date, '%Y-%m-%d').date()

                processed_count += 1

                # Build event title and description
                subject = f"{event_name} - {hebrew_name}"

                body_parts = [
                    f"<h3>פרטי אירוע</h3>",
                    f"<p><strong>שם אירוע:</strong> {event_name}</p>",
                    f"<p><strong>סוג:</strong> {event_type}</p>",
                    f"<p><strong>מועד:</strong> {hebrew_name}</p>",
                    f"<p><strong>תאריך:</strong> {deadline_date.strftime('%d/%m/%Y')}</p>",
                    f"<p><strong>ועדה:</strong> {committee_type_name} - {hativa_name}</p>",
                    f"<p><strong>בקשות צפויות:</strong> {expected_requests}</p>",
                ]

                if actual_submissions:
                    body_parts.append(f"<p><strong>הגשות בפועל:</strong> {actual_submissions}</p>")

                body = "\n".join(body_parts)

                # Calculate content hash to check if anything changed
                content_data = {
                    'subject': subject,
                    'start_date': str(deadline_date),
                    'body': body
                }
                content_hash = hashlib.md5(json.dumps(content_data, sort_keys=True).encode('utf-8')).hexdigest()

                # Check if sync record exists for this deadline
                sync_record = self.db.get_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email)

                try:
                    if sync_record and sync_record.get('calendar_event_id'):
                        # Check if content changed by comparing hash
                        stored_hash = sync_record.get('content_hash')
                        if stored_hash == content_hash and sync_record.get('sync_status') == 'synced':
                            # Content hasn't changed, skip update
                            synced_count += 1
                            continue
                        
                        # Update existing event (content changed or status is pending/failed)
                        calendar_event_id = sync_record['calendar_event_id']
                        success, message = self.update_calendar_event(
                            event_id=calendar_event_id,
                            subject=subject,
                            start_date=deadline_date,
                            body=body,
                            is_all_day=True
                        )

                        if success:
                            self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', calendar_event_id, content_hash=content_hash)
                            synced_count += 1
                        else:
                            # If update fails with 404 (event not found), recreate it
                            if 'ErrorItemNotFound' in message or '404' in message:
                                logger.info(f"Calendar event {calendar_event_id} no longer exists, recreating")
                                self.db.update_calendar_sync_status(sync_record['sync_id'], 'pending', None, error_message=message)
                                # Try to create a new event immediately
                                success2, new_cal_id, create_msg = self.create_calendar_event(
                                    subject=subject,
                                    start_date=deadline_date,
                                    body=body,
                                    is_all_day=True
                                )
                                if success2:
                                    self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', new_cal_id, content_hash=content_hash)
                                    synced_count += 1
                                else:
                                    self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=create_msg)
                                    failed_count += 1
                            else:
                                # For other errors, keep the existing calendar_event_id but mark as failed
                                self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', calendar_event_id, error_message=message)
                                failed_count += 1
                    else:
                        # Create new event (no sync record or no calendar_event_id)
                        success, cal_event_id, message = self.create_calendar_event(
                            subject=subject,
                            start_date=deadline_date,
                            body=body,
                            is_all_day=True
                        )

                        if success:
                            if sync_record:
                                # Update existing sync record with new event ID
                                self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced', cal_event_id, content_hash=content_hash)
                            else:
                                # Create new sync record
                                sync_id = self.db.create_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email, cal_event_id)
                                self.db.update_calendar_sync_status(sync_id, 'synced', cal_event_id, content_hash=content_hash)
                            synced_count += 1
                        else:
                            if sync_record:
                                self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=message)
                            else:
                                sync_id = self.db.create_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email)
                                self.db.update_calendar_sync_status(sync_id, 'failed', error_message=message)
                            failed_count += 1
                except Exception as deadline_error:
                    logger.error(f"Error syncing deadline {field_name} for event {event_id}: {deadline_error}")
                    failed_count += 1

            if processed_count == 0:
                # No deadlines configured for this event – treat as successful no-op
                return True, "No deadlines to sync"
            if synced_count > 0 and failed_count == 0:
                return True, f"Successfully synced {synced_count} deadlines"
            elif synced_count > 0:
                return True, f"Synced {synced_count} deadlines, {failed_count} failed"
            else:
                return False, f"Failed to sync deadlines: {failed_count} failed"

        except Exception as e:
            logger.error(f"Error syncing event deadlines {event_id}: {e}", exc_info=True)
            return False, str(e)

    def _sync_all_internal(self) -> Dict[str, any]:
        """
        Internal method to perform full calendar sync without acquiring lock
        Should only be called when lock is already held or from sync_all()

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting full calendar sync...")

        committees_synced = 0
        events_synced = 0
        failures = 0

        try:
            # Get all active (non-deleted) committees
            committees = self.db.get_vaadot(include_deleted=False)

            for committee in committees:
                vaadot_id = committee.get('vaadot_id')
                try:
                    success, message = self.sync_committee_to_calendar(vaadot_id)
                    if success:
                        committees_synced += 1
                    else:
                        logger.warning(f"Failed to sync committee {vaadot_id}: {message}")
                        failures += 1
                except Exception as e:
                    logger.error(f"Error syncing committee {vaadot_id}: {e}")
                    failures += 1

            # Get all active (non-deleted) events
            events = self.db.get_all_events(include_deleted=False)

            for event in events:
                event_id = event.get('event_id')
                try:
                    success, message = self.sync_event_deadlines_to_calendar(event_id)
                    if success:
                        events_synced += 1
                    else:
                        logger.warning(f"Failed to sync event {event_id}: {message}")
                        failures += 1
                except Exception as e:
                    logger.error(f"Error syncing event {event_id}: {e}")
                    failures += 1

            logger.info(f"Calendar sync complete - Committees: {committees_synced}, Events: {events_synced}, Failures: {failures}")

            return {
                'success': True,
                'message': f'Sync complete: {committees_synced} committees, {events_synced} events',
                'committees_synced': committees_synced,
                'events_synced': events_synced,
                'failures': failures
            }

        except Exception as e:
            logger.error(f"Error in full calendar sync: {e}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'committees_synced': committees_synced,
                'events_synced': events_synced,
                'failures': failures
            }

    def sync_all(self) -> Dict[str, any]:
        """
        Perform full calendar sync of all committees and events

        Returns:
            Dictionary with sync statistics
        """
        if not self.is_enabled():
            return {
                'success': False,
                'message': 'Calendar sync is disabled',
                'committees_synced': 0,
                'events_synced': 0,
                'failures': 0
            }

        # Acquire lock to prevent concurrent sync/reset operations
        # Use non-blocking acquire to avoid blocking the scheduler if a reset is in progress
        lock_acquired = self._sync_lock.acquire(blocking=False)
        if not lock_acquired:
            logger.warning("Calendar sync skipped - another sync or reset operation is in progress")
            return {
                'success': False,
                'message': 'Calendar sync skipped - another operation in progress',
                'committees_synced': 0,
                'events_synced': 0,
                'failures': 0
            }

        try:
            return self._sync_all_internal()
        finally:
            # Always release the lock
            self._sync_lock.release()
            logger.debug("Calendar sync lock released")

    def delete_all_calendar_events_and_reset(self) -> Dict[str, any]:
        """
        Delete all calendar events created by the system and reset sync records
        Then perform a full sync to recreate all events

        Returns:
            Dictionary with operation statistics
        """
        if not self.is_enabled():
            return {
                'success': False,
                'message': 'Calendar sync is disabled',
                'events_deleted': 0,
                'records_cleared': 0,
                'committees_synced': 0,
                'events_synced': 0,
                'failures': 0
            }

        # Acquire lock to prevent concurrent sync operations during reset
        # Use blocking acquire since reset is a critical operation that should wait
        logger.info("Acquiring lock for calendar reset operation...")
        with self._sync_lock:
            logger.info("Lock acquired - starting deletion of all calendar events and reset...")

            events_deleted = 0
            deletion_failures = 0
            records_cleared = 0

            try:
                # Get all synced calendar events
                sync_records = self.db.get_all_synced_calendar_events(self.calendar_email)

                logger.info(f"Found {len(sync_records)} calendar events to delete")

                # Delete each calendar event
                for record in sync_records:
                    calendar_event_id = record.get('calendar_event_id')
                    if calendar_event_id:
                        try:
                            success, message = self.delete_calendar_event(calendar_event_id)
                            if success:
                                events_deleted += 1
                            else:
                                logger.warning(f"Failed to delete calendar event {calendar_event_id}: {message}")
                                deletion_failures += 1
                        except Exception as e:
                            logger.error(f"Error deleting calendar event {calendar_event_id}: {e}")
                            deletion_failures += 1

                # Clear all sync records
                records_cleared = self.db.clear_all_calendar_sync_records(self.calendar_email)
                logger.info(f"Cleared {records_cleared} sync records from database")

                # Now perform full sync to recreate all events
                # Call internal method since we already hold the lock
                logger.info("Starting full sync to recreate all events...")
                sync_result = self._sync_all_internal()

                logger.info("Calendar reset and re-sync complete - lock will be released")

                return {
                    'success': True,
                    'message': f'Reset complete: Deleted {events_deleted} events, cleared {records_cleared} records. Re-synced: {sync_result["committees_synced"]} committees, {sync_result["events_synced"]} events',
                    'events_deleted': events_deleted,
                    'deletion_failures': deletion_failures,
                    'records_cleared': records_cleared,
                    'committees_synced': sync_result.get('committees_synced', 0),
                    'events_synced': sync_result.get('events_synced', 0),
                    'failures': sync_result.get('failures', 0) + deletion_failures
                }

            except Exception as e:
                logger.error(f"Error in delete_all_calendar_events_and_reset: {e}", exc_info=True)
                return {
                    'success': False,
                    'message': str(e),
                    'events_deleted': events_deleted,
                    'deletion_failures': deletion_failures,
                    'records_cleared': records_cleared,
                    'committees_synced': 0,
                    'events_synced': 0,
                    'failures': deletion_failures
                }
