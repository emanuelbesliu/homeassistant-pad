"""Binary sensor platform for the PAD Romania integration."""

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_POLICY_FOUND,
    ATTR_VALID_UNTIL,
    ATTR_LAST_CHECK,
    CONF_POLICY_NAME,
)
from .coordinator import PadDataUpdateCoordinator
from .sensor import _parse_date

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PAD Romania binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        PadPolicyValidBinarySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class PadPolicyValidBinarySensor(
    CoordinatorEntity[PadDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor that is ON when the PAD policy is valid/active."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PadDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_valid"
        self._attr_name = "Policy Valid"
        self._attr_icon = "mdi:shield-home"

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

    @property
    def is_on(self) -> bool | None:
        """Return True if the policy is found and not expired."""
        if self.coordinator.data is None:
            return None

        if not self.coordinator.data.get(ATTR_POLICY_FOUND, False):
            return False

        # Check expiry date
        valid_until = self.coordinator.data.get(ATTR_VALID_UNTIL)
        if valid_until:
            try:
                expiry = _parse_date(valid_until)
                if expiry:
                    return expiry >= datetime.now()
            except (ValueError, TypeError):
                pass

        # Policy found but can't determine validity — assume valid
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        if self.coordinator.data is None:
            return attrs

        for key in (ATTR_POLICY_FOUND, ATTR_VALID_UNTIL, ATTR_LAST_CHECK):
            value = self.coordinator.data.get(key)
            if value is not None:
                attrs[key] = value

        return attrs
