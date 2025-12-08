"""Calendar platform for ChoreControl."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ChoreControlDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreControl calendar platform."""
    coordinator: ChoreControlDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]
    async_add_entities([ChoreControlCalendar(coordinator)])


class ChoreControlCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for ChoreControl chores."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_chores_calendar"
        self._attr_name = "ChoreControl Chores"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self._get_events_for_range(
            date.today(),
            date.today() + timedelta(days=7),
        )
        if events:
            return events[0]
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date
        return self._get_events_for_range(start, end)

    def _get_events_for_range(
        self,
        start: date,
        end: date,
    ) -> list[CalendarEvent]:
        """Get events for a date range."""
        if not self.coordinator.data:
            return []

        events = []
        instances = self.coordinator.data.get("instances", [])
        today = date.today()

        for inst in instances:
            # Skip completed/rejected/missed instances
            status = inst.get("status")
            if status in ("approved", "rejected", "missed"):
                continue

            due_date_str = inst.get("due_date")

            if due_date_str:
                try:
                    if "T" in due_date_str:
                        due_date = datetime.fromisoformat(
                            due_date_str.replace("Z", "+00:00")
                        ).date()
                    else:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    due_date = today
            else:
                # "Anytime" chores show on today
                due_date = today

            # Check if in range
            if start <= due_date <= end:
                chore_data = inst.get("chore", {})
                chore_name = chore_data.get(
                    "name", inst.get("chore_name", "Unknown Chore")
                )

                # Get assignee info
                assignee_name = None
                if inst.get("assigned_to"):
                    user = self.coordinator.get_user_by_id(inst["assigned_to"])
                    if user:
                        assignee_name = user.get("username")

                # Build description
                description_parts = []
                if assignee_name:
                    description_parts.append(f"Assigned to: {assignee_name}")
                if chore_data.get("points"):
                    description_parts.append(f"Points: {chore_data['points']}")
                description_parts.append(f"Status: {status}")

                events.append(
                    CalendarEvent(
                        start=due_date,
                        end=due_date + timedelta(days=1),
                        summary=chore_name,
                        description="\n".join(description_parts),
                    )
                )

        # Sort by date
        events.sort(key=lambda e: e.start)
        return events

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }
