"""skills/backlink-finder/SKILL.md'yi repo köküne kopyalar.

Neden: Eski `git clone ... ~/.claude/skills/backlink-finder` kurulumları SKILL.md'yi repo kökünde arar;
plugin ise skills/backlink-finder/SKILL.md'yi kullanır. İki dosya hep aynı olmalı.
SKILL.md her değiştiğinde commit'ten önce çalıştır:  python3 scripts/kok_skill_esitle.py
"""
import os
import shutil

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
src = os.path.join(root, 'skills', 'backlink-finder', 'SKILL.md')
dst = os.path.join(root, 'SKILL.md')
shutil.copyfile(src, dst)
print(f'✓ {dst} güncellendi')
