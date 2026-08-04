import json
import base64
import zlib

# Load c27 trace to understand exact timings
with open('agent_c27.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
trace_match = re.search(r'_TRACE\s*=\s*json\.loads\(zlib\.decompress\(base64\.b85decode\(\s*\'(.*?)\'\s*\)\)\.decode\("utf-8"\)\)', content, re.DOTALL)
b85_str = trace_match.group(1).replace('\n', '').replace(' ', '').replace("'", "")
_C27_TRACE = json.loads(zlib.decompress(base64.b85decode(b85_str)).decode("utf-8"))

print(f"Loaded c27 trace with {len(_C27_TRACE)} turns.")

# Check exact steps where c27 sells MELON, MILK, WOOL, STRAWBERRY
print("\n--- Key c27 Sales Timings (Step & Hour) ---")
for step, turn in enumerate(_C27_TRACE):
    for m in turn.get("market", []):
        if isinstance(m, list) and len(m) >= 3 and m[0] == "SELL":
            if m[1] in ["MELON", "WOOL", "MILK", "STRAWBERRY"] and m[2] >= 10:
                day = step // 24
                hour = step % 24
                print(f"Step {step:3d} (Day {day:02d} Hr {hour:02d}): SELL {m[1]} x {m[2]}")
