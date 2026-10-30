import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from collections import defaultdict
from app.prompts import L1_NAME_MATCH_SYSTEM, L2_ADDRESS_MATCH_SYSTEM, SHADOW_CHECKS_SYSTEM, L3_CHECKLIST_SYSTEM_TEMPLATE
from app.assistant import ASSISTANT_SYSTEM_PROMPT

SYSTEM_PROMPTS = {
    'L1': L1_NAME_MATCH_SYSTEM,
    'L2': L2_ADDRESS_MATCH_SYSTEM,
    'shadow': SHADOW_CHECKS_SYSTEM,
    'L3': L3_CHECKLIST_SYSTEM_TEMPLATE,
    'assistant_chat': ASSISTANT_SYSTEM_PROMPT,
}

lines = [json.loads(l) for l in open('data/runtime/llm_log.jsonl', encoding='utf-8')]
total_calls = len(lines)

task_stats = defaultdict(lambda: {'calls': 0, 'input_chars': 0, 'output_chars': 0, 'latency_sum': 0})
model_stats = defaultdict(lambda: {'calls': 0, 'input_chars': 0, 'output_chars': 0, 'latency_sum': 0})

for item in lines:
    task = item.get('task', 'unknown')
    model = item.get('model', 'unknown')
    inp = item.get('redacted_input', '') or ''
    out = item.get('raw_output', '') or ''
    lat = item.get('latency_ms', 0) or 0
    sys_p = SYSTEM_PROMPTS.get(task, '')
    
    total_inp = len(sys_p) + len(inp)
    total_out = len(out)
    
    task_stats[task]['calls'] += 1
    task_stats[task]['input_chars'] += total_inp
    task_stats[task]['output_chars'] += total_out
    task_stats[task]['latency_sum'] += lat
    
    model_stats[model]['calls'] += 1
    model_stats[model]['input_chars'] += total_inp
    model_stats[model]['output_chars'] += total_out
    model_stats[model]['latency_sum'] += lat

print(f"Total Inference Calls Logged: {total_calls:,}\n")

tot_in_tok = 0
tot_out_tok = 0

print(f"{'Task':16} | {'Calls':>6} | {'Input Tokens':>14} | {'Output Tokens':>14} | {'Avg Latency':>12}")
print("-" * 72)
for t, s in sorted(task_stats.items()):
    in_tok = round(s['input_chars'] / 4)
    out_tok = round(s['output_chars'] / 4)
    tot_in_tok += in_tok
    tot_out_tok += out_tok
    avg_lat = s['latency_sum'] / max(1, s['calls'])
    print(f"{t:16} | {s['calls']:6d} | {in_tok:14,d} | {out_tok:14,d} | {avg_lat:10.1f} ms")

print("-" * 72)
print(f"{'TOTAL':16} | {total_calls:6d} | {tot_in_tok:14,d} | {tot_out_tok:14,d} |")
print(f"Grand Total Tokens across whole project: {tot_in_tok + tot_out_tok:,}\n")

# Model breakdown
print(f"{'Model':25} | {'Calls':>6} | {'Input Tokens':>14} | {'Output Tokens':>14}")
print("-" * 65)
for m, s in sorted(model_stats.items()):
    in_tok = round(s['input_chars'] / 4)
    out_tok = round(s['output_chars'] / 4)
    print(f"{m:25} | {s['calls']:6d} | {in_tok:14,d} | {out_tok:14,d}")
print("-" * 65)

# Financial Accounting:
# Gemini 2.5 Flash Lite pricing: $0.10 / 1M prompt tokens, $0.40 / 1M output tokens
gemini_cost = (tot_in_tok / 1_000_000) * 0.10 + (tot_out_tok / 1_000_000) * 0.40
gpt4o_mini_cost = (tot_in_tok / 1_000_000) * 0.15 + (tot_out_tok / 1_000_000) * 0.60
claude_haiku_cost = (tot_in_tok / 1_000_000) * 0.80 + (tot_out_tok / 1_000_000) * 4.00

print("\n--- Project Cost Figures (All 2,552 Calls) ---")
print(f"Gemini 2.5 Flash Lite (Active Engine) : ${gemini_cost:.4f}  (~PKR {gemini_cost * 280:.2f})")
print(f"GPT-4o-mini                           : ${gpt4o_mini_cost:.4f}  (~PKR {gpt4o_mini_cost * 280:.2f})")
print(f"Claude 3.5 Haiku                      : ${claude_haiku_cost:.4f}  (~PKR {claude_haiku_cost * 280:.2f})")

# Live Gemini subset (actually billed over network)
live_lines = [l for l in lines if l.get('provider') == 'gemini']
live_in_tok = sum(round((len(SYSTEM_PROMPTS.get(l.get('task'), '')) + len(l.get('redacted_input', '') or '')) / 4) for l in live_lines)
live_out_tok = sum(round(len(l.get('raw_output', '') or '') / 4) for l in live_lines)
live_cost = (live_in_tok / 1_000_000) * 0.10 + (live_out_tok / 1_000_000) * 0.40
print(f"\nLive Gemini API Direct Billed (170 Live Calls):")
print(f"Input Tokens: {live_in_tok:,} | Output Tokens: {live_out_tok:,} | Incurred Cost: ${live_cost:.4f} (~PKR {live_cost * 280:.2f})")

# Per-Case figures (Single Full Verification Run)
# A typical case calls L1 (210 in, 50 out), L2 (190 in, 50 out), Shadow (110 in, 25 out), and if trap, L3 (220 in, 65 out)
single_case_in = 210 + 190 + 110 + 220
single_case_out = 50 + 50 + 25 + 65
single_case_cost = (single_case_in / 1_000_000) * 0.10 + (single_case_out / 1_000_000) * 0.40
print(f"\nSingle Case Full Application Run:")
print(f"Tokens: ~{single_case_in:,} input + ~{single_case_out:,} output = ~{single_case_in + single_case_out:,} tokens")
print(f"Cost per case: ${single_case_cost:.6f} (~PKR {single_case_cost * 280:.4f})")

# 21 Benchmark Suite Run
suite_in = single_case_in * 21
suite_out = single_case_out * 21
suite_cost = single_case_cost * 21
print(f"\nFull 21 Benchmark Suite Run (C01 - C21):")
print(f"Tokens: ~{suite_in:,} input + ~{suite_out:,} output = ~{suite_in + suite_out:,} tokens")
print(f"Cost for full 21-case benchmark: ${suite_cost:.4f} (~PKR {suite_cost * 280:.2f})")
