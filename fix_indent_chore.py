with open("agent_jules.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_block = False
for line in lines:
    if "if worker_idx < 3:" in line:
        in_block = True
        new_lines.append(line)
        continue

    if in_block:
        if line.startswith("        # Crop Actions"):
            in_block = False
            new_lines.append(line)
            continue

        if line.strip():
            if line.startswith("                "):
                new_lines.append(line[4:])
            elif line.startswith("            "):
                new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open("agent_jules.py", "w") as f:
    f.writelines(new_lines)
