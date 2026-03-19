"""Expiry alert system for the PAD Romania integration.

Fires HA events and creates persistent notifications when a PAD policy
is approaching expiry or has expired.

Alert presets:
- Conservative: 60, 30, 14, 7 days + daily from 7 days
- Standard: 30, 14, 7 days + daily from 7 days
- Minimal: 7 days + daily from 7 days
- Off: no alerts
"""

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    ATTR_POLICY_FOUND,
    ATTR_VALID_UNTIL,
    ALERT_PRESETS,
    ALERT_PRESET_OFF,
    CONF_ALERT_PRESET,
    DEFAULT_ALERT_PRESET,
    EVENT_POLICY_EXPIRING,
    CONF_POLICY_NAME,
    CONF_SERIE_POLITA,
    CONF_NUMAR_POLITA,
)

_LOGGER = logging.getLogger(__name__)


class PadExpiryAlerts:
    """Manages expiry alerts for a single PAD policy entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the alert manager."""
        self._hass = hass
        self._entry = entry
        # Track which threshold alerts have been fired
        self._fired_thresholds: set[int] = set()
        # Track the last date we sent a daily alert (at most once per day)
        self._last_daily_alert_date: str | None = None
        self._unsub: Any = None

    def _get_preset_config(self) -> dict[str, Any]:
        """Get the active alert preset configuration from entry options."""
        preset_key = self._entry.options.get(
            CONF_ALERT_PRESET,
            self._entry.data.get(CONF_ALERT_PRESET, DEFAULT_ALERT_PRESET),
        )
        return ALERT_PRESETS.get(preset_key, ALERT_PRESETS[DEFAULT_ALERT_PRESET])

    @property
    def _policy_label(self) -> str:
        """Return a human-readable label for this policy."""
        name = self._entry.data.get(CONF_POLICY_NAME)
        if name:
            return name
        serie = self._entry.data.get(CONF_SERIE_POLITA, "")
        numar = self._entry.data.get(CONF_NUMAR_POLITA, "")
        return f"PAD {serie} {numar}".strip()

    def register(self, coordinator: DataUpdateCoordinator) -> None:
        """Register listener on coordinator updates."""
        self._unsub = coordinator.async_add_listener(self._on_update)

    def unregister(self) -> None:
        """Unregister listener."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _on_update(self) -> None:
        """Handle coordinator data update — check if alerts are needed."""
        # Check if alerts are disabled
        preset_key = self._entry.options.get(
            CONF_ALERT_PRESET,
            self._entry.data.get(CONF_ALERT_PRESET, DEFAULT_ALERT_PRESET),
        )
        if preset_key == ALERT_PRESET_OFF:
            return

        entry_data = self._hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if not entry_data:
            return

        coordinator = entry_data.get("coordinator")
        if not coordinator or not coordinator.data:
            return

        data = coordinator.data
        if not data.get(ATTR_POLICY_FOUND, False):
            return

        valid_until = data.get(ATTR_VALID_UNTIL)
        if not valid_until:
            return

        days_left = self._calc_days_left(valid_until)
        if days_left is None:
            return

        self._check_alerts(days_left)

    def _calc_days_left(self, valid_until: str) -> int | None:
        """Calculate days remaining until expiry."""
        from .sensor import _parse_date

        try:
            expiry = _parse_date(valid_until)
            if expiry:
                delta = expiry - datetime.now()
                return delta.days
        except (ValueError, TypeError):
            pass
        return None

    def _check_alerts(self, days_left: int) -> None:
        """Determine if an alert should be sent based on days_left and preset."""
        preset = self._get_preset_config()
        thresholds = preset["thresholds"]
        daily_below = preset["daily_below"]
        today = datetime.now().strftime("%Y-%m-%d")

        # Check milestone thresholds
        for threshold in thresholds:
            if (
                days_left <= threshold
                and threshold not in self._fired_thresholds
            ):
                self._fired_thresholds.add(threshold)
                # Only fire milestone if we're not also in daily mode
                if days_left > daily_below:
                    self._send_alert(days_left)
                    return

        # Daily alerts: at or below daily_below days, and when expired
        if daily_below >= 0 and days_left <= daily_below:
            if self._last_daily_alert_date != today:
                self._last_daily_alert_date = today
                self._send_alert(days_left)

    def _send_alert(self, days_left: int) -> None:
        """Fire event and create persistent notification."""
        label = self._policy_label
        serie = self._entry.data.get(CONF_SERIE_POLITA, "")
        numar = self._entry.data.get(CONF_NUMAR_POLITA, "")

        if days_left < 0:
            abs_days = abs(days_left)
            title = f"PAD Policy Expired — {label}"
            message = (
                f"Polița PAD {label} ({serie} {numar}) a expirat "
                f"acum {abs_days} {'zi' if abs_days == 1 else 'zile'}. "
                f"Reînnoiți urgent pe padrom.ro!"
            )
            severity = "expired"
        elif days_left == 0:
            title = f"PAD Policy Expires Today — {label}"
            message = (
                f"Polița PAD {label} ({serie} {numar}) expiră astăzi! "
                f"Reînnoiți urgent pe padrom.ro!"
            )
            severity = "expires_today"
        else:
            title = f"PAD Policy Expiring — {label}"
            message = (
                f"Polița PAD {label} ({serie} {numar}) expiră în "
                f"{days_left} {'zi' if days_left == 1 else 'zile'}. "
                f"Reînnoiți pe padrom.ro."
            )
            severity = "expiring_soon"

        # Fire HA event
        event_data = {
            "entry_id": self._entry.entry_id,
            "policy_label": label,
            "policy_series": serie,
            "policy_number": numar,
            "days_left": days_left,
            "severity": severity,
            "title": title,
            "message": message,
        }
        self._hass.bus.async_fire(EVENT_POLICY_EXPIRING, event_data)
        _LOGGER.info(
            "PAD expiry alert fired: %s (%d days left)", label, days_left
        )

        # Create persistent notification
        notification_id = f"pad_expiry_{self._entry.entry_id}"
        self._hass.components.persistent_notification.async_create(
            message=message,
            title=title,
            notification_id=notification_id,
        )
