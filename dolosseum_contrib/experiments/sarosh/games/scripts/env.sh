# Source this file (bash or zsh) to point the packaged experiments at the pinned upstream bundle.
#   source scripts/env.sh                                  # default: games/vendor/collusion_hackathon
#   DOLOS_BUNDLE=/path/to/collusion_hackathon source scripts/env.sh
# Only sets paths; no keys, no network. Values already set in the environment are kept.

if [ -n "${ZSH_VERSION:-}" ]; then
  _dolos_src="${(%):-%x}"
else
  _dolos_src="${BASH_SOURCE[0]}"
fi
_dolos_games="$(cd "$(dirname "$_dolos_src")/.." && pwd)"
unset _dolos_src

export DOLOS_BUNDLE="${DOLOS_BUNDLE:-$_dolos_games/vendor/collusion_hackathon}"
export LLM_CARTEL_ROOT="${LLM_CARTEL_ROOT:-$DOLOS_BUNDLE/llm-cartel}"
export COLOSSEUM_ROOT="${COLOSSEUM_ROOT:-$DOLOS_BUNDLE/colosseum}"
export LIARS_BAR_UPSTREAM="${LIARS_BAR_UPSTREAM:-$DOLOS_BUNDLE/llm-agent-collusion-2/Collusion_Liars_Bar}"
export REDTEAMING_ROOT="${REDTEAMING_ROOT:-$DOLOS_BUNDLE/redteaming}"
# poseidon_compute (shared inference layer that llm-cartel imports): put the bundle's util/ folder on the path.
export PYTHONPATH="$DOLOS_BUNDLE/util${PYTHONPATH:+:$PYTHONPATH}"
unset _dolos_games
