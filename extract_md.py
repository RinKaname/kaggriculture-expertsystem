import json

with open("kaggriculture-frontier-lab-high-score-visuals.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for i, cell in enumerate(nb.get("cells", [])):
    if cell.get("cell_type") == "markdown":
        print(f"\n==================== [Cell {i}] ====================")
        print("".join(cell.get("source", [])))
