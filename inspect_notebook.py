import json
import sys

nb_path = "kaggriculture-frontier-lab-high-score-visuals.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

output_lines = []
output_lines.append(f"Total cells: {len(nb.get('cells', []))}\n")

for i, cell in enumerate(nb.get("cells", [])):
    cell_type = cell.get("cell_type")
    source = "".join(cell.get("source", []))
    if cell_type == "markdown":
        output_lines.append(f"\n========================================\n[Cell {i}] Markdown:\n========================================\n{source}\n")
    elif cell_type == "code":
        output_lines.append(f"\n----------------------------------------\n[Cell {i}] Code:\n----------------------------------------\n{source}\n")

with open("notebook_dump.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Dumped {len(nb.get('cells', []))} cells to notebook_dump.txt")
