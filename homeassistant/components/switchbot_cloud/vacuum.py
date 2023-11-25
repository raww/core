"""Support for SwitchBot switch."""
from typing import Any

from switchbot_api import Device, SwitchBotAPI, VacuumCommands

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SwitchbotCloudData
from .const import DOMAIN
from .coordinator import SwitchBotCoordinator
from .entity import SwitchBotCloudEntity

_SWITCHBOT_VACUUM_STATE_MAP: dict[str, str] = {
    "StandBy": STATE_IDLE,
    "ChargeDone": STATE_IDLE,
    "Dormant": STATE_IDLE,
    "Clearing": STATE_CLEANING,
    "Paused": STATE_PAUSED,
    "GotoChargeBase": STATE_RETURNING,
    "InDustCollecting": STATE_RETURNING,
    "Charging": STATE_DOCKED,
    "InTrouble": STATE_ERROR,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SwitchBot Cloud entry."""
    data: SwitchbotCloudData = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        _async_make_entity(data.api, device, coordinator)
        for device, coordinator in data.devices.vacuums
    )


class SwitchBotVacuum(SwitchBotCloudEntity, StateVacuumEntity):
    """Representation of a SwitchBot Robot Vacuum."""

    _attr_supported_features = (
        VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.STATUS
    )

    async def async_start(self) -> None:
        """Start or resume cleaning."""
        await self._send_command(VacuumCommands.START)
        self._attr_state = STATE_CLEANING
        await self.async_update_ha_state()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return the vacuum to its dock."""
        await self._send_command(VacuumCommands.DOCK)
        self._attr_state = STATE_RETURNING
        await self.async_update_ha_state()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning or pause cleaning."""
        await self._send_command(VacuumCommands.STOP)
        self._attr_state = STATE_PAUSED
        await self.async_update_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self.coordinator.data:
            return

        status = self.coordinator.data.get("workingStatus")
        if status is None:
            return

        self._attr_state: str = _SWITCHBOT_VACUUM_STATE_MAP.get(status, STATE_ERROR)
        self._attr_battery_level = self.coordinator.data.get("battery")
        self.async_write_ha_state()


@callback
def _async_make_entity(
    api: SwitchBotAPI, device: Device, coordinator: SwitchBotCoordinator
) -> SwitchBotVacuum:
    return SwitchBotVacuum(api, device, coordinator)
