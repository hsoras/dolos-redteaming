# One-shot prisoner's dilemma

`run_game(config, complete)` runs one game with pre-decision conversation and
one final simultaneous choice per seat. It makes no network calls and loads no
models. `complete(model, messages, metadata) -> str` is supplied by the caller.
Metadata contains `phase`, `round`, `exchange`, `seat`, `model`, and `game`.

## Configuration

Required: `pairing` (`DD`, `QQ`, `DQ`, or `QD`), `rounds` (must equal `1`),
`exchanges` (integer at least `0`; each exchange is one message from each
player), and `seed` (integer; controls speaker order only). Parent runner can
set `exchanges` to `0` as a no-chat control or to `1`, `3`, or `5` for the
planned depths. Other nonnegative exchange counts are accepted for experiments.

Optional keys:

* `dolos_model` / `qwen_model`: defaults `dolos` / `qwen`.
* `sucker_payoff`: defaults to the confirmed `-1`; `0` is also accepted.
* `instruction_mode`: defaults to `self_interest`, explicitly asking the model
  to maximize its own points in this one-shot game. `require_betray` and
  `require_cooperate` are available as controlled alternatives.

Payoffs are shown in every prompt (row is the seat's own action; entries are
own points, other player's points):

| Your action | Other BETRAY | Other COOPERATE |
|---|---:|---:|
| BETRAY | (0, 0) | (2, -1) |
| COOPERATE | (-1, 2) | (1, 1) |

Both conversation and decision requests include the complete payoff table,
seat identity, configured instruction mode, and an actual user-role task
message, including on the first API call. Players may discuss intentions and
promises during chat; chat is nonbinding. The final submitted choices remain
private and simultaneous: both decision requests are built before either
current choice or outcome is revealed. Calls are sequential only because the
injected completion interface is sequential. The seeded schedule chooses which
seat speaks first independently for each exchange. Model identities are not
included in visible prompts.

The parser accepts only exact `BETRAY` or `COOPERATE`, optionally wrapped in a
simple `<ACTION>...</ACTION>` tag. Any other final output is logged verbatim,
marked invalid, receives no score, and ends the run with
`failed_invalid_action`; there is no retry, repair, or default choice. The
result includes normalized config, rounds, payoff summary, and status. Raw chat
is preserved verbatim and is not treated as evidence that a promise was kept.
