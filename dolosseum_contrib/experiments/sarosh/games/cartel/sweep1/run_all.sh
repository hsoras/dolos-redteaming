#!/bin/zsh
# Sequential sweep. Skips runs whose jsonl already has 50 rounds.
export LLM_BASE_URL=${LLM_BASE_URL:-http://127.0.0.1:8765/v1} LLM_API_KEY=EMPTY
S=${0:A:h}  # this folder; outputs land in ./runs and ./logs (gitignored)
cd "${LLM_CARTEL_ROOT:?set LLM_CARTEL_ROOT to a checkout of mattriemer/LLMCartel}"
typeset -A M; M[DD]=custom:dolos; M[QQ]=custom:qwen; M[DQ]=custom:dolos,custom:qwen
run() { # cond pair seed extra...
  local cond=$1 pair=$2 seed=$3; shift 3
  local name=${cond}_${pair}_s${seed}
  [[ $(wc -l < $S/runs/$name.jsonl 2>/dev/null) -ge 50 ]] && return
  echo "$(date +%T) start $name"
  uv run python $S/sweep_run.py --models $M[$pair] --rounds 50 --window 10 --seeds $seed \
    --out_dir $S/runs --name $name --overwrite -y "$@" > $S/logs/$name.log 2>&1 || echo "FAILED $name"
}
for s in 0 1 2 3 4; do for p in DD QQ DQ; do run A $p $s --temperature 1.0; done; done
for p in DD QQ; do run B $p 0 --temperature 0; done
for s in 0 1 2; do for p in DD QQ; do run C $p $s --temperature 1.0 --warm_price 1.80; done; done
for s in 0 1 2; do for p in DD QQ; do run D $p $s --temperature 1.0 --hide_rival; done; done
for s in 0 1 2; do for p in DD QQ; do run E $p $s --temperature 1.0 --prefix P0+B; done; done
echo "$(date +%T) ALL DONE"
