"""CPU-only HF-template replay for one captured vLLM chat request.

Usage: python replay_execution_prompt.py /path/to/pinned-qwen-tokenizer
Requires transformers/tokenizers and the complete tokenizer snapshot. No model weights.
"""
import json
import os
import sys
from transformers import AutoTokenizer

capture = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../inputs/colosseum-captures/execution_request.json")))
request = capture["request"]
tokenizer = AutoTokenizer.from_pretrained(sys.argv[1], local_files_only=True)
tools = request.get("tools")
# vLLM 0.10.1.1 ChatCompletionRequest validator sets omitted tool_choice to auto
# when tools exist; serving passes tools unless choice=none AND exclusion enabled.
rendered = tokenizer.apply_chat_template(
    request["messages"], tools=tools, tokenize=False, add_generation_prompt=True
)
ids = tokenizer.apply_chat_template(
    request["messages"], tools=tools, tokenize=True, add_generation_prompt=True
)
print("tool_choice: auto (vLLM request default)")
print("assign_task in rendered prompt:", "assign_task" in rendered)
print("prompt_tokens:", len(ids), "observed:", capture["observed_prompt_tokens"])
print(rendered)
