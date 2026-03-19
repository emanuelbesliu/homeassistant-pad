"""Config flow for the PAD Romania integration."""

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import PadApi, PadApiError
from .const import (
    DOMAIN,
    CONF_SERIE_POLITA,
    CONF_NUMAR_POLITA,
    CONF_CNP_CUI,
    CONF_UPDATE_INTERVAL,
    CONF_POLICY_NAME,
    CONF_ALERT_PRESET,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ALERT_PRESET,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    VALID_SERIES,
    ALERT_PRESET_CONSERVATIVE,
    ALERT_PRESET_STANDARD,
    ALERT_PRESET_MINIMAL,
    ALERT_PRESET_OFF,
)

_LOGGER = logging.getLogger(__name__)


class PadConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PAD Romania."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step — enter policy credentials."""
        errors = {}

        if user_input is not None:
            serie = user_input[CONF_SERIE_POLITA]
            numar = user_input[CONF_NUMAR_POLITA]
            cnp = user_input[CONF_CNP_CUI]

            # Validate policy number format (digits only)
            if not re.match(r"^\d+$", numar):
                errors[CONF_NUMAR_POLITA] = "invalid_number"
            # Validate CNP/CUI format (digits only)
            elif not re.match(r"^\d+$", cnp):
                errors[CONF_CNP_CUI] = "invalid_cnp"
            else:
                # Set unique ID based on serie + number
                unique_id = f"{serie}_{numar}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Test connection
                api = PadApi()
                try:
                    await self.hass.async_add_executor_job(
                        api.validate_connection, serie, numar, cnp
                    )
                except PadApiError:
                    errors["base"] = "cannot_connect"
                finally:
                    api.close()

                if not errors:
                    policy_name = user_input.get(
                        CONF_POLICY_NAME, f"PAD {serie} {numar}"
                    )
                    if not policy_name:
                        policy_name = f"PAD {serie} {numar}"

                    return self.async_create_entry(
                        title=policy_name,
                        data={
                            CONF_SERIE_POLITA: serie,
                            CONF_NUMAR_POLITA: numar,
                            CONF_CNP_CUI: cnp,
                            CONF_POLICY_NAME: policy_name,
                            CONF_UPDATE_INTERVAL: user_input.get(
                                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                            ),
                        },
                    )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SERIE_POLITA): vol.In(VALID_SERIES),
                vol.Required(CONF_NUMAR_POLITA): str,
                vol.Required(CONF_CNP_CUI): str,
                vol.Optional(CONF_POLICY_NAME, default=""): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return PadOptionsFlowHandler()


class PadOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for PAD Romania."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            ),
        )

        current_alert_preset = self.config_entry.options.get(
            CONF_ALERT_PRESET,
            self.config_entry.data.get(
                CONF_ALERT_PRESET, DEFAULT_ALERT_PRESET
            ),
        )

        alert_preset_options = {
            ALERT_PRESET_CONSERVATIVE: "Conservative (60, 30, 14, 7 days + daily)",
            ALERT_PRESET_STANDARD: "Standard (30, 14, 7 days + daily)",
            ALERT_PRESET_MINIMAL: "Minimal (7 days + daily)",
            ALERT_PRESET_OFF: "Off",
        }

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
                vol.Optional(
                    CONF_ALERT_PRESET,
                    default=current_alert_preset,
                ): vol.In(alert_preset_options),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
