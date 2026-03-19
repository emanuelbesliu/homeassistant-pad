"""Sensor platform for the PAD Romania integration."""

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_VALID_UNTIL,
    ATTR_LAST_CHECK,
    ATTR_POLICY_FOUND,
    CONF_POLICY_NAME,
)
from .coordinator import PadDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PAD Romania sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        PadPolicyStatusSensor(coordinator, entry),
        PadPolicyExpirySensor(coordinator, entry),
        PadDaysUntilExpirySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class PadBaseSensor(
    CoordinatorEntity[PadDataUpdateCoordinator], SensorEntity
):
    """Base class for PAD sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PadDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{sensor_key}"
        self._attr_name = name
        self._attr_icon = icon

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the PAD policy."""
        policy_name = self._entry.data.get(
            CONF_POLICY_NAME, "PAD Policy"
        )
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": policy_name,
            "manufacturer": "PAID Romania",
            "model": "PAD Insurance Policy",
            "entry_type": "service",
            "configuration_url": "https://www.padrom.ro",
        }


class PadPolicyStatusSensor(PadBaseSensor):
    """Sensor showing the PAD policy status."""

    def __init__(
        self,
        coordinator: PadDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the policy status sensor."""
        super().__init__(
            coordinator, entry, "status", "Policy Status", "mdi:shield-check"
        )

    @property
    def native_value(self) -> str | None:
        """Return the policy status."""
        if self.coordinator.data is None:
            return None

        if not self.coordinator.data.get(ATTR_POLICY_FOUND, False):
            return "Not Found"

        # Determine status from expiry date
        valid_until = self.coordinator.data.get(ATTR_VALID_UNTIL)
        if valid_until:
            try:
                expiry = _parse_date(valid_until)
                if expiry and expiry >= datetime.now():
                    return "Active"
                elif expiry:
                    return "Expired"
            except (ValueError, TypeError):
                pass

        return "Found"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data is None:
            return attrs

        attrs["policy_found"] = self.coordinator.data.get(
            ATTR_POLICY_FOUND, False
        )
        attrs["policy_series"] = self.coordinator.data.get(
            "policy_series", ""
        )
        attrs["policy_number"] = self.coordinator.data.get(
            "policy_number", ""
        )

        valid_until = self.coordinator.data.get(ATTR_VALID_UNTIL)
        if valid_until:
            attrs["valid_until"] = valid_until

        last_check = self.coordinator.data.get(ATTR_LAST_CHECK)
        if last_check:
            attrs["last_check"] = last_check

        return attrs


class PadPolicyExpirySensor(PadBaseSensor):
    """Sensor showing the PAD policy expiry date."""

    def __init__(
        self,
        coordinator: PadDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the policy expiry sensor."""
        super().__init__(
            coordinator, entry, "expiry", "Policy Expiry", "mdi:calendar-clock"
        )

    @property
    def native_value(self) -> str | None:
        """Return the policy expiry date."""
        if self.coordinator.data is None:
            return None

        if not self.coordinator.data.get(ATTR_POLICY_FOUND, False):
            return None

        return self.coordinator.data.get(ATTR_VALID_UNTIL)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data is None:
            return attrs

        last_check = self.coordinator.data.get(ATTR_LAST_CHECK)
        if last_check:
            attrs["last_check"] = last_check

        return attrs


class PadDaysUntilExpirySensor(PadBaseSensor):
    """Sensor showing days until PAD policy expires."""

    def __init__(
        self,
        coordinator: PadDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the days until expiry sensor."""
        super().__init__(
            coordinator,
            entry,
            "days_until_expiry",
            "Days Until Expiry",
            "mdi:calendar-alert",
        )
        self._attr_native_unit_of_measurement = "days"

    @property
    def native_value(self) -> int | None:
        """Return days until policy expires."""
        if self.coordinator.data is None:
            return None

        if not self.coordinator.data.get(ATTR_POLICY_FOUND, False):
            return None

        valid_until = self.coordinator.data.get(ATTR_VALID_UNTIL)
        if not valid_until:
            return None

        try:
            expiry = _parse_date(valid_until)
            if expiry:
                delta = expiry - datetime.now()
                return delta.days
        except (ValueError, TypeError):
            pass

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data is None:
            return attrs

        last_check = self.coordinator.data.get(ATTR_LAST_CHECK)
        if last_check:
            attrs["last_check"] = last_check

        valid_until = self.coordinator.data.get(ATTR_VALID_UNTIL)
        if valid_until:
            attrs["expiry_date"] = valid_until

        return attrs


def _parse_date(date_str: str) -> datetime | None:
    """Parse a date string in common Romanian formats.

    Supports: DD-MM-YYYY, DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD

    Args:
        date_str: The date string to parse.

    Returns:
        datetime object or None if parsing fails.
    """
    formats = [
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d.%m.%y",
        "%d/%m/%y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None
