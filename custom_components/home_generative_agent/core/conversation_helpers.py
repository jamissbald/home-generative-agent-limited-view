"""Helper utilities for conversation processing."""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import TYPE_CHECKING, Any, cast

import yaml
from .state_filter import get_filtered_states

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
# ... (existing constants)

def _resolve_entity_id(entity_id: str, hass: HomeAssistant) -> str:
    """Try to resolve a suggested entity_id to an existing sandboxed entity_id."""
    if not _ENTITY_ID_PATTERN.match(entity_id):
        return entity_id

    # 🔒 CHANGE: Ensure the candidate pool is already filtered
    allowed_states = get_filtered_states(hass)
    allowed_ids = {s.entity_id for s in allowed_states}

    if entity_id in allowed_ids:
        return entity_id

    domain, object_id = entity_id.split(".", 1)
    prefix = f"{domain}."
    
    candidates = [
        state.entity_id
        for state in allowed_states
        if state.entity_id.startswith(prefix)
    ]
    
    if not candidates:
        return entity_id

    def score_match(candidate: str) -> float:
        candidate_obj = candidate.split(".", 1)[1]
        ratio = difflib.SequenceMatcher(None, object_id, candidate_obj).ratio()
        target_tokens = {token for token in object_id.split("_") if token}
        candidate_tokens = {token for token in candidate_obj.split("_") if token}
        overlap = 0.0
        if target_tokens:
            overlap = len(target_tokens & candidate_tokens) / len(target_tokens)
        return ratio + (overlap * _ENTITY_ID_TOKEN_OVERLAP_WEIGHT)

    tokens = [token for token in object_id.split("_") if token]
    if tokens:
        token_matches = [
            candidate
            for candidate in candidates
            if all(token in candidate.split(".", 1)[1] for token in tokens)
        ]
        if token_matches:
            best_match = max(token_matches, key=score_match)
            if score_match(best_match) >= _ENTITY_ID_MATCH_SCORE_MIN:
                return best_match

    scored = max(candidates, key=score_match)
    if score_match(scored) >= _ENTITY_ID_MATCH_SCORE_MIN:
        return scored

    close = difflib.get_close_matches(
        entity_id, candidates, n=1, cutoff=_ENTITY_ID_MATCH_SCORE_MIN
    )
    return close[0] if close else entity_id

# ... (keep remaining card/dashboard fix functions)
