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
        return PLUGIN in name
    if hook == 'prompt':
        prompt = str(payload.get('prompt', '')).strip().lower()
        return prompt.startswith(f'/{PLUGIN}')
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
        if not relevant(a.hook, payload):
            sys.exit(0)
    status, loc, rem = check()
    if status == 'eski':
        print(UPDATE_MSG.format(local=loc, remote=rem), file=sys.stderr)
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
    sys.exit(0)
