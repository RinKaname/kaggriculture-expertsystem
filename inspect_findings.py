import json

with open('kaggriculture-findings-from-zero-to-top-meta.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print(f"Total cells: {len(nb.get('cells', []))}")

with open('findings_dump.md', 'w', encoding='utf-8') as out:
    out.write(f"# Findings Notebook Dump (Total Cells: {len(nb.get('cells', []))})\n\n")
    for i, cell in enumerate(nb.get('cells', [])):
        cell_type = cell.get('cell_type')
        source = "".join(cell.get('source', []))
        if cell_type == 'markdown':
            out.write(f"\n## Cell {i} [MARKDOWN]\n\n{source}\n\n---\n")
        elif cell_type == 'code':
            out.write(f"\n## Cell {i} [CODE]\n\n```python\n{source}\n```\n\n---\n")

print("Dumped findings notebook to findings_dump.md successfully!")
