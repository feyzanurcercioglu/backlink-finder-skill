"""Kurulu plugin sürümünü GitHub'daki son sürümle karşılaştırır; eskiyse çalışmayı engeller.

Kullanım:
    python3 surum_kontrol.py                 # skill ilk adımı: çıktı + çıkış kodu
    python3 surum_kontrol.py --hook pretool  # PreToolUse(Skill) hook'u: stdin JSON
    python3 surum_kontrol.py --hook prompt   # UserPromptSubmit hook'u: stdin JSON

Çıkış kodları:
    0  güncel (ya da hook ilgisiz bir çağrı için tetiklendi)
    2  ESKİ SÜRÜM: çalışma engellenir, güncelleme komutu stderr'e yazılır
    0 + uyarı  GitHub'a ulaşılamadı (internet yok): engellemez, uyarır
"""
import argparse
import json
import os
import re
import sys
import urllib.request

REPO = 'feyzanurcercioglu/backlink-finder-skill'
REMOTE = f'https://raw.githubusercontent.com/{REPO}/main/.claude-plugin/plugin.json'
PLUGIN = 'backlink-finder'
MARKET = 'inbound-seo'
ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

UPDATE_MSG = f"""⛔ Backlink Finder plugin'iniz güncel değil (kurulu: {{local}}, güncel: {{remote}}).
Bu sürümle çalışma yapılamaz; mecra listesi ve kurallar eski olabilir.

Güncellemek için terminalde şu satırı çalıştırın:
  claude plugin marketplace update {MARKET} && claude plugin update {PLUGIN}@{MARKET}

ya da Claude Code içinde:
  1) /plugin marketplace update {MARKET}
  2) /plugin  > Installed > {PLUGIN} > Update now

Sonra Claude Code'u yeniden başlatıp çalışmayı tekrar isteyin.
Kalıcı çözüm: /plugin > Marketplaces > {MARKET} > Enable auto-update"""


LEGACY_DIRS = [os.path.expanduser('~/.claude/skills/backlink-finder'), os.path.expanduser('~/.claude/skills/backlink-skill')]
LEGACY_CMD = re.compile(r'^/(backlink-skill|backlink-finder)(\s|$)', re.I)   # '/backlink-finder:backlink-finder' hariç
LEGACY_MSG = """⛔ Bu Backlink komutunun ({cmd}) arkasındaki kopya eski. Eski sürüm aracı mecra Excel'ini sorar ve güncel kuralları içermez.

Doğru komut:  /backlink-finder:backlink-finder
(ya da doğrudan yazın: "Dagi için Kasım backlink çalışması hazırla")

Eski kopyaları kaldırın:
  - Terminal: rm -rf ~/.claude/skills/backlink-finder ~/.claude/skills/backlink-skill
  - claude.ai > Settings > Capabilities > Skills: "backlink-skill"i kapatın ya da silin
Sonra Claude Code'u yeniden başlatın."""


CLONE_MSG = """⛔ Backlink Finder skill'iniz güncel değil (kurulu: {{local}}, güncel: {{remote}}).
Bu sürümle çalışma yapılamaz; mecra listesi ve kurallar eski olabilir.

Güncellemek için terminalde:
  git -C "{root}" pull

Sonra Claude Code'u yeniden başlatıp çalışmayı tekrar isteyin.
(Önerilen: plugin kurulumuna geçin, güncellemeler otomatik gelir:
  claude plugin marketplace add {repo} && claude plugin install {plugin}@{market})"""


SKILL_MSG = """⛔ Bu Backlink skill'i (claude.ai'a yüklenen "backlink-skill") güncel değil (yüklü: {local}, güncel: {remote}).
Bu sürümle çalışma yapılamaz; mecra listesi ve kurallar eski.

Yöneticinize haber verin: claude.ai > Settings > Capabilities > Skills'te "backlink-skill" yeni paketle değiştirilmeli.
Bu arada güncel sürümü Claude Code'da plugin olarak kullanabilirsiniz (güncellemeler otomatik gelir):
  claude plugin marketplace add {repo} && claude plugin install {plugin}@{market}
  komut: /backlink-finder:backlink-finder"""


def is_uploaded_skill():
    """claude.ai'a yüklenip senkronize edilen kopya (Claude Code: ~/.claude/skills/synced/...; claude.ai VM: /mnt/skills/...)."""
    r = os.path.realpath(ROOT)
    return '/skills/synced/' in r or r.startswith('/mnt/skills') or os.path.basename(r) == 'backlink-skill'


def synced_copies_current(remote):
    """Senkronize 'backlink-skill' kopyalarından biri güncel sürümdeyse True."""
    import glob
    for pj in glob.glob(os.path.expanduser('~/.claude/skills/synced/*/backlink-skill/.claude-plugin/plugin.json')):
        try:
            if vtuple(json.load(open(pj, encoding='utf-8')).get('version')) >= vtuple(remote):
                return True
        except Exception:  # noqa: BLE001
            pass
    return False


def is_clone():
    return os.path.isdir(os.path.join(ROOT, '.git'))


def legacy_copies():
    here = os.path.realpath(ROOT)
    return [d for d in LEGACY_DIRS if os.path.isdir(d) and os.path.realpath(d) != here]


def vtuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:3]) or (0,)


def local_version():
    with open(os.path.join(ROOT, '.claude-plugin', 'plugin.json'), encoding='utf-8') as f:
        return json.load(f).get('version', '0.0.0')


def remote_version(timeout=5):
    req = urllib.request.Request(REMOTE, headers={'Cache-Control': 'no-cache', 'User-Agent': 'backlink-finder'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8')).get('version', '0.0.0')


def check():
    """(durum, local, remote) -> durum: 'ok' | 'eski' | 'bilinmiyor'"""
    loc = local_version()
    try:
        rem = remote_version()
    except Exception:  # noqa: BLE001  internet yok / GitHub erişilemez
        return 'bilinmiyor', loc, None
    return ('eski' if vtuple(loc) < vtuple(rem) else 'ok'), loc, rem


def relevant(hook, payload):
    if hook == 'pretool':
        name = str((payload.get('tool_input') or {}).get('skill', ''))
        return name.startswith(PLUGIN + ':')
    if hook == 'prompt':
        prompt = str(payload.get('prompt', '')).strip().lower()
        return prompt.startswith(f'/{PLUGIN}:')
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--hook', choices=['pretool', 'prompt'])
    a = ap.parse_args()
    if a.hook:
        try:
            payload = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            payload = {}
        cmd = None
        if a.hook == 'prompt':
            m = LEGACY_CMD.match(str(payload.get('prompt', '')).strip())
            cmd = ('/' + m.group(1).lower()) if m else None
        if a.hook == 'pretool':
            name = str((payload.get('tool_input') or {}).get('skill', ''))
            if name.split(':')[-1] == 'backlink-skill' or name == 'backlink-finder':
                cmd = name
        if cmd:
            if cmd.endswith('backlink-skill'):
                # claude.ai'a yüklenen tam sürüm güncelse çalışmasına izin ver
                try:
                    rem = remote_version()
                except Exception:  # noqa: BLE001
                    sys.exit(0)
                if synced_copies_current(rem):
                    sys.exit(0)
            print(LEGACY_MSG.format(cmd=cmd), file=sys.stderr)
            sys.exit(2)
        if not relevant(a.hook, payload):
            sys.exit(0)
    status, loc, rem = check()
    if status == 'eski':
        if is_clone():
            msg = CLONE_MSG.format(root=os.path.realpath(ROOT), repo=REPO, plugin=PLUGIN, market=MARKET).format(local=loc, remote=rem)
        elif is_uploaded_skill():
            msg = SKILL_MSG.format(local=loc, remote=rem, repo=REPO, plugin=PLUGIN, market=MARKET)
        else:
            msg = UPDATE_MSG.format(local=loc, remote=rem)
        print(msg, file=sys.stderr)
        if not a.hook:
            print(f'SURUM_ESKI kurulu={loc} guncel={rem}')
        sys.exit(2)
    if status == 'bilinmiyor':
        msg = f'⚠ GitHub\'a ulaşılamadı, sürüm doğrulanamadı (kurulu: {loc}). İnternet bağlantısını kontrol edin.'
        print(msg, file=sys.stderr)
        if not a.hook:
            print(f'SURUM_BILINMIYOR kurulu={loc}')
        sys.exit(0)
    if not a.hook:
        print(f'SURUM_GUNCEL {loc}')
        old = legacy_copies()
        if old:
            print('ESKI_KOPYA ' + ' '.join(old))
            print('⚠ Bilgisayarınızda eski Backlink skill kopyası var: ' + ', '.join(old)
                  + '\n  Kaldırmak için: rm -rf ' + ' '.join(old), file=sys.stderr)
    sys.exit(0)
