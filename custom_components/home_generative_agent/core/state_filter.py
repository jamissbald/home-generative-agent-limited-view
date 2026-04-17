from homeassistant.core import HomeAssistant, State

def get_sandboxed_states(hass: HomeAssistant) -> list[State]:
    """Base layer: returns all states to satisfy dependencies safely."""
    return list(hass.states.async_all())

def get_filtered_states(hass: HomeAssistant) -> list[State]:
    """Central filter for HGASentinel labelled entities."""
    allowed_label = "HGASentinel"

    return [
        state
        for state in get_sandboxed_states(hass)
        if allowed_label in (state.attributes.get("labels") or [])
    ]
