import os, glob

base_dir = r"C:\Users\donro\OneDrive\Desktop\Google-Antigravity-IDE-Database-Sync---Fix"
paths = glob.glob(os.path.join(base_dir, "src", "*.py"))
paths.append(os.path.join(base_dir, "antigravity_recover.py"))

for path in paths:
    with open(path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    with open(path, 'w', encoding='utf-8') as file:
        for line in lines:
            stripped = line.rstrip()
            if stripped:
                file.write(stripped + '\n')
            else:
                file.write('\n')
