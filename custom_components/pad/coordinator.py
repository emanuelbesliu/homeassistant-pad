"""Data update coordinator for the PAD Romania integration."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import PadApi, PadApiError
from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL,
    CONF_SERIE_POLITA,
    CONF_NUMAR_POLITA,
    CONF_CNP_CUI,
)

_LOGGER = logging.getLogger(__name__)


class PadDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from PAD Romania API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PadApi,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.entry = entry

        update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the PAD Romania API.

        Returns:
            dict with policy verification data.

        Raises:
            UpdateFailed: If the API request fails.
        """
        serie = self.entry.data[CONF_SERIE_POLITA]
        numar = self.entry.data[CONF_NUMAR_POLITA]
        cnp = self.entry.data[CONF_CNP_CUI]

        try:
            data = await self.hass.async_add_executor_job(
                self.api.verify_policy, serie, numar, cnp
            )
        except PadApiError as err:
            raise UpdateFailed(f"Error fetching PAD data: {err}") from err

        if data is None:
            raise UpdateFailed("PAD API returned empty data")

        _LOGGER.debug("PAD policy data updated: %s", data)
        return data
