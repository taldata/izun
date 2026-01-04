from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import logging

from database import DatabaseManager

logger = logging.getLogger(__name__)


def _nearest_five_events(events: List[Dict]) -> List[Dict]:
    """
    Select up to five nearest events relative to now.
    Priority: upcoming events by ascending date; if fewer than five, backfill with most recent past events.
    """
    now = datetime.now()

    def to_datetime(ev: Dict) -> Optional[datetime]:
        # Prefer scheduled_date if present; else use call_deadline_date; else intake/review/response; else created_at
        for key in (
            "scheduled_date",
            "call_deadline_date",
            "intake_deadline_date",
            "review_deadline_date",
            "response_deadline_date",
            "created_at",
        ):
            val = ev.get(key)
            if not val:
                continue
            try:
                # Accept both date ('YYYY-MM-DD') and datetime ('YYYY-MM-DD HH:MM:SS')
                if isinstance(val, datetime):
                    return val
                if isinstance(val, date):
                    return datetime(val.year, val.month, val.day)
                if isinstance(val, str):
                    if " " in val:
                        return datetime.fromisoformat(val.replace(" ", "T"))
                    return datetime.fromisoformat(val)
            except Exception:
                continue
        return None

    with_dates: List[Tuple[Optional[datetime], Dict]] = [(to_datetime(ev), ev) for ev in events]
    upcoming = sorted([ev for ev in with_dates if ev[0] and ev[0] >= now], key=lambda x: x[0])  # type: ignore[arg-type]
    past = sorted([ev for ev in with_dates if ev[0] and ev[0] < now], key=lambda x: x[0], reverse=True)  # type: ignore[arg-type]

    selected = [ev for _, ev in upcoming[:5]]
    if len(selected) < 5:
        selected += [ev for _, ev in past[: 5 - len(selected)]]
    return selected


def get_committee_summary(database: DatabaseManager, vaadot_id: int) -> Dict:
    """
    Build a summary object for a committee (vaada) including key details and up to 5 nearest events.
    """
    try:
        logger.info(f"Getting summary for committee {vaadot_id}")
        vaada = database.get_vaada_by_id(vaadot_id)
        if not vaada:
            logger.warning(f"Committee {vaadot_id} not found")
            return {"success": False, "message": "ועדה לא נמצאה"}

        # Get all events for this committee
        events = database.get_events(vaadot_id=vaadot_id)
        logger.info(f"Found {len(events)} events for committee {vaadot_id}")

        # Select nearest five
        nearest = _nearest_five_events(events)

        # Map minimal fields for UI
        def map_event(ev: Dict) -> Dict:
            return {
                "event_id": ev.get("event_id"),
                "title": ev.get("name"),
                "location": ev.get("hativa_name"),  # no explicit location in schema; reuse division as proxy
                "start": ev.get("scheduled_date") or ev.get("call_deadline_date"),
                "end": ev.get("response_deadline_date"),
                "event_type": ev.get("event_type"),
                "maslul_name": ev.get("maslul_name"),
                "expected_requests": ev.get("expected_requests") or 0,
                "actual_submissions": ev.get("actual_submissions") or 0,
            }

        summary = {
            "success": True,
            "committee": {
                "vaadot_id": vaada.get("vaadot_id"),
                "name": vaada.get("committee_name"),
                "type_id": vaada.get("committee_type_id"),
                "hativa_id": vaada.get("hativa_id"),
                "hativa_name": vaada.get("hativa_name"),
                "date": vaada.get("vaada_date"),
            },
            "nearest_events": [map_event(ev) for ev in nearest],
            "counts": {
                "total_events": len(events),
                "nearest_count": len(nearest),
            },
        }
        return summary

    except Exception as e:
        logger.error(f"Error generating committee summary: {e}", exc_info=True)
        return {"success": False, "message": "שגיאה בטעינת הנתונים"}


