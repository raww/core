"""Config flow for SwitchBot via API integration."""

from logging import getLogger
from typing import Any

from switchbot_api import CannotConnect, InvalidAuth, SwitchBotAPI
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_API_TOKEN
from homeassistant.components import cloud
from homeassistant.const import CONF_API_KEY, CONF_API_TOKEN, CONF_WEBHOOK_ID

from .const import CONFIGURE_WEBHOOK, DOMAIN, ENTRY_TITLE

_LOGGER = getLogger(__name__)

_COMMON_SCHEMA = {vol.Required(CONF_API_TOKEN): str, vol.Required(CONF_API_KEY): str}

STEP_USER_DATA_SCHEMA = vol.Schema(_COMMON_SCHEMA)

STEP_USER_DATA_SCHEMA_WITH_CLOUD = vol.Schema(
    {
        **_COMMON_SCHEMA,
        vol.Required(CONFIGURE_WEBHOOK, default=True): bool,
    }
)


class SwitchBotCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SwitchBot via API."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        cloud_available = (
            "cloud" in self.hass.config.components
            and self.hass.components.cloud.async_active_subscription()
            and self.hass.components.cloud.async_is_connected()
        )
        if user_input is not None:
            try:
                api = SwitchBotAPI(
                    token=user_input[CONF_API_TOKEN], secret=user_input[CONF_API_KEY]
                )
                await api.list_devices()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_API_TOKEN], raise_on_progress=False
                )
                self._abort_if_unique_id_configured()

                data = user_input.copy()

                if cloud_available and user_input[CONFIGURE_WEBHOOK]:
                    _LOGGER.debug("Configuring webhook")
                    webhook_id = self.hass.components.webhook.async_generate_id()
                    webhook_url = await cloud.async_create_cloudhook(
                        self.hass, webhook_id
                    )
                    data[CONF_WEBHOOK_ID] = webhook_id
                    await api.setup_webhook(webhook_url)

                return self.async_create_entry(title=ENTRY_TITLE, data=data)

        data_schema = (
            STEP_USER_DATA_SCHEMA_WITH_CLOUD
            if cloud_available
            else STEP_USER_DATA_SCHEMA
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
