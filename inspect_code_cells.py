import json

with open("kaggriculture-frontier-lab-high-score-visuals.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

for i in [4, 6, 8, 9, 10, 11, 12, 13, 15, 17, 19, 20, 22]:
    if i < len(nb.get("cells", [])):
        cell = nb["cells"][i]
        print(f"\n==================== [Cell {i}] Code ====================")
        src = "".join(cell.get("source", []))
        print(src[:600])
