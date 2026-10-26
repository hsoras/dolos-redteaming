#!/usr/bin/env bash
# Fetch the pinned Liar's Bar upstream source (sparse, one game directory) into vendor/.
# Source: https://github.com/poseidon-research/collusion_hackathon (starter commit d585a7b).
# Existing checkouts are verified, never overwritten: wrong commit or local changes -> exit 1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="https://github.com/poseidon-research/collusion_hackathon.git"
PIN="d585a7b3be50366cc2bdf5789bf8add5890b2abd"
SPARSE_PATH="llm-agent-collusion-2/Collusion_Liars_Bar"
DEST="$ROOT/vendor/collusion_hackathon"

if [[ -e "$DEST" && ! -d "$DEST/.git" ]]; then
  echo >&2 "$DEST exists but is not a git checkout; move it aside and rerun."; exit 1
fi
if [[ ! -d "$DEST/.git" ]]; then
  mkdir -p "$DEST"
  git -C "$DEST" init --quiet
  git -C "$DEST" remote add origin "$REPO_URL"
  git -C "$DEST" sparse-checkout set "$SPARSE_PATH"
  git -C "$DEST" fetch --quiet --depth 1 --filter=blob:none origin "$PIN"
  git -C "$DEST" checkout --quiet --detach "$PIN"
fi

CURRENT="$(git -C "$DEST" rev-parse HEAD)"
if [[ "$CURRENT" != "$PIN" ]]; then
  echo >&2 "vendor/collusion_hackathon is at $CURRENT, expected pinned $PIN."
  echo >&2 "Not overwriting. Move it aside, or set LIARS_BAR_UPSTREAM to a checkout at the pin."
  exit 1
fi
if [[ -n "$(git -C "$DEST" status --porcelain)" ]]; then
  echo >&2 "vendor/collusion_hackathon has local changes; not overwriting. Revert them or move it aside."
  exit 1
fi
GAME="$DEST/$SPARSE_PATH"
[[ -f "$GAME/src/game/game.py" ]] || { echo >&2 "Upstream game missing at $GAME"; exit 1; }
printf 'Pinned Liar'"'"'s Bar upstream: %s\n' "$CURRENT"
printf 'Game directory: %s\n' "$GAME"
