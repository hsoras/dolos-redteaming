"""Door relay one-shot game. See README.md for prompts, parser, and limitations."""

from .game import (
    ALLOWED_EXCHANGES,
    DEFAULTS,
    GAME_NAME,
    ConfigError,
    door_schedule,
    lexical_flags,
    normalize_config,
    parse_choice,
    run_game,
    summarize_results,
)

__all__ = [
    "ALLOWED_EXCHANGES",
    "DEFAULTS",
    "GAME_NAME",
    "ConfigError",
    "door_schedule",
    "lexical_flags",
    "normalize_config",
    "parse_choice",
    "run_game",
    "summarize_results",
]
