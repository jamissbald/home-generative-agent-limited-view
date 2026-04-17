"""Langgraph tools for Home Generative Agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from homeassistant.core import HomeAssistant
from .camera_activity import get_camera_last_events_from_states
from ..core.conversation_helpers import _resolve_entity_id

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------
# STUBS TO PREVENT IMPORT CRASHES
# -------------------------------------------------------------
def analyze_image(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

def get_and_analyze_camera_image(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

def add_automation(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

# -------------------------------------------------------------
# FIXED ENTITY LOOKUP
# -------------------------------------------------------------
async def _get_existing_entity_id(
    name: str | None,
    hass: HomeAssistant,
    domain: str | None = "sensor",
) -> str:
    """Lookup entity by friendly name (HGASentinel filtered version)."""
    from ..core.state_filter import get_filtered_states

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Name must be a non-empty string")

    if not isinstance(domain, str):
        raise ValueError("Invalid domain")

    target = name.strip().lower()
    prefix = f"{domain}."
    
    # Get only the sandboxed states
    candidates = [
        state.entity_id
        for state in get_filtered_states(hass)
        if state.entity_id.startswith(prefix) and 
           state.attributes.get("friendly_name", "").lower() == target
    ]

    if not candidates:
        raise ValueError(f"No '{domain}' entity found with friendly name '{name}' in sandbox.")

    if len(candidates) > 1:
        raise ValueError(f"Multiple matches found in sandbox: {candidates}")

    return candidates[0]

# [Your original tool definitions like resolve_entity_ids, etc., continue here...]
