import json

with open("kaggriculture-frontier-lab-high-score-visuals.ipynb", "r", encoding="utf-8") as f:
    nb = json.load(f)

md_content = []
for i, cell in enumerate(nb.get("cells", [])):
    if cell.get("cell_type") == "markdown":
        md_content.append(f"\n==================== [Cell {i}] ====================\n")
        md_content.append("".join(cell.get("source", [])))

with open("all_notebook_markdown.md", "w", encoding="utf-8") as f:
    f.write("".join(md_content))

print("Extracted all markdown successfully!")
