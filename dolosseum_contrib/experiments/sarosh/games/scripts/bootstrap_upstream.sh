#!/usr/bin/env bash
# Fetch the official poseidon-research/collusion_hackathon bundle at the pinned commit into games/vendor/.
#
#   scripts/bootstrap_upstream.sh                 # NETWORK: clone (or fetch) and check out the pin
#   scripts/bootstrap_upstream.sh --verify-only   # OFFLINE: check an existing copy against the pin, no fetch, no checkout
#   scripts/bootstrap_upstream.sh --verify-only /path/to/collusion_hackathon
#
# Nothing in the experiments calls this script; run it yourself when you want the vendored code.
set -euo pipefail

URL="${BUNDLE_URL:-https://github.com/poseidon-research/collusion_hackathon}"  # override only for mirrors or a local-path test clone
PIN_COMMIT="d585a7b3be50366cc2bdf5789bf8add5890b2abd"
# subtree name : tree object id at PIN_COMMIT (content pin for the five projects this package uses)
PIN_TREES="llm-cartel:b5ab8c4748ae3998cb2a518f20621600e3a76fb0
colosseum:b06a2cda4d3f7eb6ff7355b065a9dd479e23a67a
llm-agent-collusion-2:b7ebc67047cfac559111e4df5a74973247b6eceb
util:73ebe5bc599773eda8796491cab93bb294546e2c
redteaming:67c59a8d8c2038470256c1de881f56e901adf04b"

GAMES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_ONLY=0
if [ "${1:-}" = "--verify-only" ]; then VERIFY_ONLY=1; shift; fi
DEST="${1:-$GAMES_DIR/vendor/collusion_hackathon}"

fail() { echo "FAIL: $*" >&2; exit 1; }

verify_pins() {
  local dir="$1" head
  head=$(git -C "$dir" rev-parse HEAD) || fail "$dir is not a git repository"
  [ "$head" = "$PIN_COMMIT" ] || fail "HEAD is $head, expected $PIN_COMMIT"
  [ -z "$(git -C "$dir" status --porcelain)" ] || fail "$dir has tracked or untracked changes against HEAD"
  while IFS=: read -r name tree; do
    [ -n "$name" ] || continue
    local got
    got=$(git -C "$dir" rev-parse "HEAD:$name")
    [ "$got" = "$tree" ] || fail "$name tree is $got, expected $tree"
    echo "  ok  $name  $tree"
  done <<< "$PIN_TREES"
  echo "verified: $dir @ $PIN_COMMIT (clean)"
}

if [ "$VERIFY_ONLY" = 1 ]; then
  verify_pins "$DEST"
  exit 0
fi

mkdir -p "$(dirname "$DEST")"
if [ -d "$DEST/.git" ]; then
  [ "$(git -C "$DEST" remote get-url origin)" = "$URL" ] || fail "$DEST has a different origin"
  git -C "$DEST" fetch origin
else
  git clone "$URL" "$DEST"
fi
[ -z "$(git -C "$DEST" status --porcelain)" ] || fail "$DEST has local changes; refusing to check out over them"
git -C "$DEST" -c advice.detachedHead=false checkout --detach "$PIN_COMMIT"
verify_pins "$DEST"
