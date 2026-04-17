from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

def get_sandboxed_states(hass: HomeAssistant) -> list[State]:
    """Base layer: returns all states to satisfy dependencies safely."""
    return list(hass.states.async_all())

def get_filtered_states(hass: HomeAssistant) -> list[State]:
    """
    Central filter for HGASentinel labelled entities.
    Checks the Entity Registry for the HGASentinel label.
    """
    allowed_label = "HGASentinel"
    registry = er.async_get(hass)
    
    # Create a set of entity IDs that have the required label
    allowed_ids = {
        entry.entity_id for entry in registry.entities.values()
        if entry.labels and allowed_label in entry.labels
    }

    return [
        state
        for state in hass.states.async_all()
        if state.entity_id in allowed_ids
    ]
