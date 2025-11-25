"""Service layer for managing scheduling constraints."""

import copy
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ConstraintUpdateResult:
    """Represents the outcome of a constraint update operation."""
    success: bool
    message: str
    errors: Optional[Dict[str, str]] = None


class ConstraintsService:
    """Business logic for reading and updating scheduling constraints."""

    time_pattern = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    def __init__(self, database: DatabaseManager):
        self.db = database
        self.day_options = self._build_day_options()

    def _build_day_options(self) -> List[Dict[str, Any]]:
        """Return metadata for each day of the week (Python weekday numbering)."""
        # Python weekday(): Monday=0 ... Sunday=6
        options = [
            {'value': 6, 'label': 'יום ראשון', 'short': 'א'},
            {'value': 0, 'label': 'יום שני', 'short': 'ב'},
            {'value': 1, 'label': 'יום שלישי', 'short': 'ג'},
            {'value': 2, 'label': 'יום רביעי', 'short': 'ד'},
            {'value': 3, 'label': 'יום חמישי', 'short': 'ה'},
            {'value': 4, 'label': 'יום שישי', 'short': 'ו'},
            {'value': 5, 'label': 'שבת', 'short': 'ש'},
        ]
        return options

    def _format_day_options(self, selected_days: List[int]) -> List[Dict[str, Any]]:
        """Annotate day options with selection state."""
        formatted = []
        selected_set = set(selected_days or [])
        for option in self.day_options:
            formatted.append({
                **option,
                'selected': option['value'] in selected_set
            })
        return formatted

    def _build_work_days_summary(self, options: List[Dict[str, Any]]) -> str:
        """Create a human readable summary for work days."""
        active_labels = [opt['short'] for opt in options if opt['selected']]
        if not active_labels:
            return 'לא הוגדרו ימי עבודה'
        return 'ימי עבודה: ' + ', '.join(active_labels)

    def get_constraints_overview(self) -> Dict[str, Any]:
        """Fetch current constraint settings and computed summaries."""
        logger.debug("Loading constraint overview")

        work_days = self.db.get_work_days()
        work_start = self.db.get_system_setting('work_start_time') or '08:00'
        work_end = self.db.get_system_setting('work_end_time') or '17:00'
        sla_days_before = self.db.get_int_setting('sla_days_before', 14)
        
        # Get constraint for committee date
        max_requests_committee_date = self.db.get_int_setting('max_requests_committee_date', 100)

        constraint_settings = self.db.get_constraint_settings()
        formatted_days = self._format_day_options(work_days)

        overview = {
            'work_days': {
                'options': formatted_days,
                'selected_values': work_days,
                'summary': self._build_work_days_summary(formatted_days)
            },
            'business_hours': {
                'start': work_start,
                'end': work_end,
                'range': f"{work_start} - {work_end}"
            },
            'limits': {
                'max_meetings_per_day': constraint_settings['max_meetings_per_day'],
                'max_weekly_meetings': constraint_settings['max_weekly_meetings'],
                'max_third_week_meetings': constraint_settings['max_third_week_meetings'],
                'max_requests_committee_date': max_requests_committee_date
            },
            'sla_days_before': sla_days_before,
            'recommendations': {
                'base_score': self.db.get_int_setting('rec_base_score', 100),
                'best_bonus': self.db.get_int_setting('rec_best_bonus', 25),
                'space_bonus': self.db.get_int_setting('rec_space_bonus', 10),
                'sla_bonus': self.db.get_int_setting('rec_sla_bonus', 20),
                'optimal_range_bonus': self.db.get_int_setting('rec_optimal_range_bonus', 15),
                'no_events_bonus': self.db.get_int_setting('rec_no_events_bonus', 5),
                'high_load_penalty': self.db.get_int_setting('rec_high_load_penalty', 15),
                'medium_load_penalty': self.db.get_int_setting('rec_medium_load_penalty', 5),
                'no_space_penalty': self.db.get_int_setting('rec_no_space_penalty', 50),
                'no_sla_penalty': self.db.get_int_setting('rec_no_sla_penalty', 30),
                'tight_sla_penalty': self.db.get_int_setting('rec_tight_sla_penalty', 10),
                'far_future_penalty': self.db.get_int_setting('rec_far_future_penalty', 10),
                'week_full_penalty': self.db.get_int_setting('rec_week_full_penalty', 20),
                'optimal_range_start': self.db.get_int_setting('rec_optimal_range_start', 0),
                'optimal_range_end': self.db.get_int_setting('rec_optimal_range_end', 30),
                'far_future_threshold': self.db.get_int_setting('rec_far_future_threshold', 60)
            }
        }

        logger.debug("Constraint overview loaded: %s", overview)
        return overview

    def apply_form_values(self, overview: Dict[str, Any], form_values: Dict[str, Any]) -> Dict[str, Any]:
        """Merge submitted form values into the overview structure for redisplay."""
        merged = copy.deepcopy(overview)

        if 'work_days' in form_values:
            work_days = [int(day) for day in form_values.get('work_days', [])]
            merged['work_days']['selected_values'] = work_days
            merged['work_days']['options'] = self._format_day_options(work_days)
            merged['work_days']['summary'] = self._build_work_days_summary(merged['work_days']['options'])

        if form_values.get('work_start_time'):
            merged['business_hours']['start'] = form_values['work_start_time']
        if form_values.get('work_end_time'):
            merged['business_hours']['end'] = form_values['work_end_time']
        merged['business_hours']['range'] = f"{merged['business_hours']['start']} - {merged['business_hours']['end']}"

        limits = merged.get('limits', {})
        for key in ('max_meetings_per_day', 'max_weekly_meetings', 'max_third_week_meetings',
                   'max_requests_committee_date'):
            if form_values.get(key) not in (None, ''):
                try:
                    limits[key] = int(form_values[key])
                except ValueError:
                    limits[key] = form_values[key]

        if form_values.get('sla_days_before') not in (None, ''):
            try:
                merged['sla_days_before'] = int(form_values['sla_days_before'])
            except ValueError:
                merged['sla_days_before'] = form_values['sla_days_before']

        # Update recommendation settings if present
        rec_keys = [
            'rec_base_score', 'rec_best_bonus', 'rec_space_bonus', 'rec_sla_bonus',
            'rec_optimal_range_bonus', 'rec_no_events_bonus', 'rec_high_load_penalty',
            'rec_medium_load_penalty', 'rec_no_space_penalty', 'rec_no_sla_penalty',
            'rec_tight_sla_penalty', 'rec_far_future_penalty', 'rec_week_full_penalty',
            'rec_optimal_range_start', 'rec_optimal_range_end', 'rec_far_future_threshold'
        ]
        
        recommendations = merged.get('recommendations', {})
        for key in rec_keys:
            if form_values.get(key) not in (None, ''):
                try:
                    # Remove 'rec_' prefix for the dict key
                    dict_key = key.replace('rec_', '')
                    recommendations[dict_key] = int(form_values[key])
                except ValueError:
                    dict_key = key.replace('rec_', '')
                    recommendations[dict_key] = form_values[key]

        return merged

    def parse_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and sanitize form input."""
        work_days = data.getlist('work_days') if hasattr(data, 'getlist') else data.get('work_days', [])
        if isinstance(work_days, str):
            work_days = [work_days]
        work_days = [int(day) for day in work_days if str(day).isdigit()]

        payload = {
            'work_days': sorted(set(work_days)),
            'work_start_time': (data.get('work_start_time') or '').strip(),
            'work_end_time': (data.get('work_end_time') or '').strip(),
            'sla_days_before': data.get('sla_days_before', '').strip(),
            'max_meetings_per_day': data.get('max_meetings_per_day', '').strip(),
            'max_weekly_meetings': data.get('max_weekly_meetings', '').strip(),
            'max_third_week_meetings': data.get('max_third_week_meetings', '').strip(),
            'max_requests_committee_date': data.get('max_requests_committee_date', '').strip(),
            # Recommendation parameters
            'rec_base_score': data.get('rec_base_score', '').strip(),
            'rec_best_bonus': data.get('rec_best_bonus', '').strip(),
            'rec_space_bonus': data.get('rec_space_bonus', '').strip(),
            'rec_sla_bonus': data.get('rec_sla_bonus', '').strip(),
            'rec_optimal_range_bonus': data.get('rec_optimal_range_bonus', '').strip(),
            'rec_no_events_bonus': data.get('rec_no_events_bonus', '').strip(),
            'rec_high_load_penalty': data.get('rec_high_load_penalty', '').strip(),
            'rec_medium_load_penalty': data.get('rec_medium_load_penalty', '').strip(),
            'rec_no_space_penalty': data.get('rec_no_space_penalty', '').strip(),
            'rec_no_sla_penalty': data.get('rec_no_sla_penalty', '').strip(),
            'rec_tight_sla_penalty': data.get('rec_tight_sla_penalty', '').strip(),
            'rec_far_future_penalty': data.get('rec_far_future_penalty', '').strip(),
            'rec_week_full_penalty': data.get('rec_week_full_penalty', '').strip(),
            'rec_optimal_range_start': data.get('rec_optimal_range_start', '').strip(),
            'rec_optimal_range_end': data.get('rec_optimal_range_end', '').strip(),
            'rec_far_future_threshold': data.get('rec_far_future_threshold', '').strip()
        }
        logger.debug("Parsed constraint request payload: %s", payload)
        return payload

    def _validate_time(self, value: str, field: str, errors: Dict[str, str]):
        """Validate HH:MM formatted strings."""
        if not value:
            errors[field] = 'שדה זה הוא חובה'
            return
        if not self.time_pattern.match(value):
            errors[field] = 'יש להזין שעה בפורמט HH:MM'

    def _validate_int(self, value: str, field: str, errors: Dict[str, str], *, minimum: int = 0, maximum: Optional[int] = None):
        """Validate numeric fields."""
        if value is None or value == '':
            errors[field] = 'שדה זה הוא חובה'
            return
        try:
            numeric = int(value)
        except ValueError:
            errors[field] = 'יש להזין מספר שלם'
            return
        if numeric < minimum:
            errors[field] = f'יש להזין מספר גדול או שווה ל-{minimum}'
        if maximum is not None and numeric > maximum:
            errors[field] = f'יש להזין מספר קטן או שווה ל-{maximum}'

    def _validate_payload(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Validate payload fields and return errors if any."""
        errors: Dict[str, str] = {}

        if not payload['work_days']:
            errors['work_days'] = 'יש לבחור לפחות יום עבודה אחד'

        self._validate_time(payload['work_start_time'], 'work_start_time', errors)
        self._validate_time(payload['work_end_time'], 'work_end_time', errors)

        if 'work_start_time' not in errors and 'work_end_time' not in errors:
            if payload['work_start_time'] >= payload['work_end_time']:
                errors['work_end_time'] = 'שעת הסיום חייבת להיות מאוחרת יותר משעת ההתחלה'

        self._validate_int(payload['sla_days_before'], 'sla_days_before', errors, minimum=1, maximum=180)
        self._validate_int(payload['max_meetings_per_day'], 'max_meetings_per_day', errors, minimum=1, maximum=10)
        self._validate_int(payload['max_weekly_meetings'], 'max_weekly_meetings', errors, minimum=1, maximum=30)
        self._validate_int(payload['max_third_week_meetings'], 'max_third_week_meetings', errors, minimum=1, maximum=30)
        self._validate_int(payload['max_requests_committee_date'], 'max_requests_committee_date', errors, minimum=1, maximum=1000)

        # Validate recommendation parameters
        self._validate_int(payload['rec_base_score'], 'rec_base_score', errors, minimum=0, maximum=500)
        self._validate_int(payload['rec_best_bonus'], 'rec_best_bonus', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_space_bonus'], 'rec_space_bonus', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_sla_bonus'], 'rec_sla_bonus', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_optimal_range_bonus'], 'rec_optimal_range_bonus', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_no_events_bonus'], 'rec_no_events_bonus', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_high_load_penalty'], 'rec_high_load_penalty', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_medium_load_penalty'], 'rec_medium_load_penalty', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_no_space_penalty'], 'rec_no_space_penalty', errors, minimum=0, maximum=200)
        self._validate_int(payload['rec_no_sla_penalty'], 'rec_no_sla_penalty', errors, minimum=0, maximum=200)
        self._validate_int(payload['rec_tight_sla_penalty'], 'rec_tight_sla_penalty', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_far_future_penalty'], 'rec_far_future_penalty', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_week_full_penalty'], 'rec_week_full_penalty', errors, minimum=0, maximum=100)
        self._validate_int(payload['rec_optimal_range_start'], 'rec_optimal_range_start', errors, minimum=0, maximum=365)
        self._validate_int(payload['rec_optimal_range_end'], 'rec_optimal_range_end', errors, minimum=0, maximum=365)
        self._validate_int(payload['rec_far_future_threshold'], 'rec_far_future_threshold', errors, minimum=0, maximum=365)

        if not errors:
            max_day = int(payload['max_meetings_per_day'])
            max_week = int(payload['max_weekly_meetings'])
            max_third_week = int(payload['max_third_week_meetings'])
            if max_third_week < max_week:
                errors['max_third_week_meetings'] = 'מכסת השבוע השלישי חייבת להיות גדולה או שווה למכסה השבועית'
            if max_week < max_day:
                errors['max_weekly_meetings'] = 'המכסה השבועית חייבת להיות גדולה או שווה למכסה היומית'

        return errors

    def update_constraints(self, payload: Dict[str, Any], user_id: Optional[int]) -> ConstraintUpdateResult:
        """Update system settings with validated payload."""
        logger.info("Updating constraints by user %s", user_id)
        errors = self._validate_payload(payload)
        if errors:
            logger.warning("Constraint update failed validation: %s", errors)
            return ConstraintUpdateResult(success=False, message='אנא תקנו את השגיאות והנסו שוב', errors=errors)

        if user_id is None:
            logger.error("Constraint update attempted without user context")
            return ConstraintUpdateResult(success=False, message='משתמש לא מזוהה')

        work_days_str = ','.join(str(day) for day in payload['work_days'])
        updates = {
            'work_days': work_days_str,
            'work_start_time': payload['work_start_time'],
            'work_end_time': payload['work_end_time'],
            'sla_days_before': payload['sla_days_before'],
            'max_meetings_per_day': payload['max_meetings_per_day'],
            'max_weekly_meetings': payload['max_weekly_meetings'],
            'max_third_week_meetings': payload['max_third_week_meetings'],
            'max_requests_committee_date': payload['max_requests_committee_date'],
            # Recommendation parameters
            'rec_base_score': payload['rec_base_score'],
            'rec_best_bonus': payload['rec_best_bonus'],
            'rec_space_bonus': payload['rec_space_bonus'],
            'rec_sla_bonus': payload['rec_sla_bonus'],
            'rec_optimal_range_bonus': payload['rec_optimal_range_bonus'],
            'rec_no_events_bonus': payload['rec_no_events_bonus'],
            'rec_high_load_penalty': payload['rec_high_load_penalty'],
            'rec_medium_load_penalty': payload['rec_medium_load_penalty'],
            'rec_no_space_penalty': payload['rec_no_space_penalty'],
            'rec_no_sla_penalty': payload['rec_no_sla_penalty'],
            'rec_tight_sla_penalty': payload['rec_tight_sla_penalty'],
            'rec_far_future_penalty': payload['rec_far_future_penalty'],
            'rec_week_full_penalty': payload['rec_week_full_penalty'],
            'rec_optimal_range_start': payload['rec_optimal_range_start'],
            'rec_optimal_range_end': payload['rec_optimal_range_end'],
            'rec_far_future_threshold': payload['rec_far_future_threshold']
        }

        for key, value in updates.items():
            self.db.update_system_setting(key, str(value), user_id)
            logger.debug("Updated system setting %s=%s", key, value)

        logger.info("Constraint settings updated successfully")
        return ConstraintUpdateResult(success=True, message='הגדרות האילוצים עודכנו בהצלחה')

