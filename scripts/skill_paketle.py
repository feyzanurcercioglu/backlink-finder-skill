"""claude.ai'a yüklenecek "backlink-skill" paketini repodan üretir.

Kullanım:  python3 scripts/skill_paketle.py [--out ../backlink-skill.skill]

İçerik: SKILL.md (name: backlink-skill), scripts/, data/, brands/, references/, requirements.txt,
.claude-plugin/plugin.json (sürüm kontrolü için). hooks/ ve kullanıcı dosyaları dahil edilmez.
Her sürüm artışında (aylık mecra listesi, kural değişikliği) yeniden üretilip claude.ai'a yüklenmelidir;
yüklenmezse paket eski sürümde kalır ve kendini kilitler (surum_kontrol.py).
"""
import argparse
import json
import os
import re
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INCLUDE = ['scripts', 'data', 'brands', 'references', 'requirements.txt', '.claude-plugin/plugin.json']
SKIP = re.compile(r'(__pycache__|\.pyc$|\.DS_Store|_gecmis\.csv$|skill_paketle\.py$|kok_skill_esitle\.py$)')

ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(ROOT, '..', 'backlink-skill.skill'))
a = ap.parse_args()
ver = json.load(open(os.path.join(ROOT, '.claude-plugin', 'plugin.json'), encoding='utf-8'))['version']
skill = open(os.path.join(ROOT, 'skills', 'backlink-finder', 'SKILL.md'), encoding='utf-8').read()
skill = skill.replace('name: backlink-finder', 'name: backlink-skill', 1)
with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('backlink-skill/SKILL.md', skill)
    for item in INCLUDE:
        full = os.path.join(ROOT, item)
        if os.path.isfile(full):
            z.write(full, f'backlink-skill/{item}')
            continue
        for dp, _, files in os.walk(full):
            for f in files:
                fp = os.path.join(dp, f)
                rel = os.path.relpath(fp, ROOT)
                if not SKIP.search(rel):
                    z.write(fp, f'backlink-skill/{rel}')
print(f'✓ {os.path.abspath(a.out)} (sürüm {ver})')
