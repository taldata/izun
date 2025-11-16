#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calendar Sync Service
Handles synchronization of committee meetings and event deadlines to Microsoft 365 shared calendar
Uses Microsoft Graph API with app-only authentication
"""

import requests
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date
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
                             user_email: str = None) -> Tuple[bool, Optional[str], str]:
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

            # Build event object
            event = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "start": {
                    "dateTime": start_date.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                },
                "end": {
                    "dateTime": end_date.isoformat(),
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
                              is_all_day: bool = True, user_email: str = None) -> Tuple[bool, str]:
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
                event_update["start"] = {
                    "dateTime": start_date.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                }
                event_update["isAllDay"] = is_all_day

            if end_date is not None:
                event_update["end"] = {
                    "dateTime": end_date.isoformat(),
                    "timeZone": "Asia/Jerusalem"
                }
            elif start_date is not None:
                # If start_date provided but not end_date, make them the same
                event_update["end"] = {
                    "dateTime": start_date.isoformat(),
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
            committee = self.db.get_vaada_details(vaadot_id)
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

            if not vaada_date:
                return False, "Committee has no date"

            # Parse date
            if isinstance(vaada_date, str):
                vaada_date = datetime.strptime(vaada_date, '%Y-%m-%d').date()

            # Build event title and description
            subject = f"{committee_type_name} - {hativa_name}"

            # Build HTML description with all details
            body_parts = [
                f"<h3>פרטי ועדה</h3>",
                f"<p><strong>סוג ועדה:</strong> {committee_type_name}</p>",
                f"<p><strong>חטיבה:</strong> {hativa_name}</p>",
                f"<p><strong>תאריך:</strong> {vaada_date.strftime('%d/%m/%Y')}</p>",
                f"<p><strong>סטטוס:</strong> {status}</p>",
            ]

            if is_operational:
                body_parts.append("<p><strong>ועדה תפעולית</strong></p>")

            if notes:
                body_parts.append(f"<p><strong>הערות:</strong> {notes}</p>")

            body = "\n".join(body_parts)

            # Check if sync record exists
            sync_record = self.db.get_calendar_sync_record('vaadot', vaadot_id, None, self.calendar_email)

            if sync_record and sync_record['calendar_event_id'] and sync_record['sync_status'] == 'synced':
                # Update existing event
                success, message = self.update_calendar_event(
                    event_id=sync_record['calendar_event_id'],
                    subject=subject,
                    start_date=vaada_date,
                    body=body,
                    is_all_day=True
                )

                if success:
                    self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced')
                    return True, f"Committee updated in calendar"
                else:
                    self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=message)
                    return False, message
            else:
                # Create new event
                success, event_id, message = self.create_calendar_event(
                    subject=subject,
                    start_date=vaada_date,
                    body=body,
                    is_all_day=True
                )

                if success:
                    # Create or update sync record
                    sync_id = self.db.create_calendar_sync_record('vaadot', vaadot_id, None, self.calendar_email, event_id)
                    self.db.update_calendar_sync_status(sync_id, 'synced', event_id)
                    return True, f"Committee created in calendar with ID: {event_id}"
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
            event = self.db.get_event_details(event_id)
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

            for field_name, hebrew_name in deadline_fields.items():
                deadline_date = event.get(field_name)

                if not deadline_date:
                    continue  # Skip if deadline not set

                # Parse date
                if isinstance(deadline_date, str):
                    deadline_date = datetime.strptime(deadline_date, '%Y-%m-%d').date()

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

                # Check if sync record exists for this deadline
                sync_record = self.db.get_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email)

                try:
                    if sync_record and sync_record['calendar_event_id'] and sync_record['sync_status'] == 'synced':
                        # Update existing event
                        success, message = self.update_calendar_event(
                            event_id=sync_record['calendar_event_id'],
                            subject=subject,
                            start_date=deadline_date,
                            body=body,
                            is_all_day=True
                        )

                        if success:
                            self.db.update_calendar_sync_status(sync_record['sync_id'], 'synced')
                            synced_count += 1
                        else:
                            self.db.update_calendar_sync_status(sync_record['sync_id'], 'failed', error_message=message)
                            failed_count += 1
                    else:
                        # Create new event
                        success, cal_event_id, message = self.create_calendar_event(
                            subject=subject,
                            start_date=deadline_date,
                            body=body,
                            is_all_day=True
                        )

                        if success:
                            sync_id = self.db.create_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email, cal_event_id)
                            self.db.update_calendar_sync_status(sync_id, 'synced', cal_event_id)
                            synced_count += 1
                        else:
                            sync_id = self.db.create_calendar_sync_record('event_deadline', event_id, field_name, self.calendar_email)
                            self.db.update_calendar_sync_status(sync_id, 'failed', error_message=message)
                            failed_count += 1
                except Exception as deadline_error:
                    logger.error(f"Error syncing deadline {field_name} for event {event_id}: {deadline_error}")
                    failed_count += 1

            if synced_count > 0 and failed_count == 0:
                return True, f"Successfully synced {synced_count} deadlines"
            elif synced_count > 0:
                return True, f"Synced {synced_count} deadlines, {failed_count} failed"
            else:
                return False, f"Failed to sync deadlines: {failed_count} failed"

        except Exception as e:
            logger.error(f"Error syncing event deadlines {event_id}: {e}", exc_info=True)
            return False, str(e)

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

        logger.info("Starting full calendar sync...")

        committees_synced = 0
        events_synced = 0
        failures = 0

        try:
            # Get all active (non-deleted) committees
            committees = self.db.get_all_vaadot()

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
            events = self.db.get_all_events()

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
