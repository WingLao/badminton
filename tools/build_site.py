#!/usr/bin/env python3
"""每週整站更新：同步本機來源、產生研究頁、重建首頁／分類目錄／更新紀錄。

用法（在 badminton 儲存庫根目錄）：
    python3 tools/build_site.py              # 以澳門時間今天為日期
    python3 tools/build_site.py --date 2026-11-23

只會寫入儲存庫內的檔案；不提交、不推送。部署由 tools/weekly_update.sh 處理。
需要：Python 3、pandoc（把 Markdown 轉成網頁的工具）。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import filecmp
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading_card as RC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]          # 網站資料/badminton
SRC = ROOT.parent                                   # 網站資料
NOTES = SRC / '學術/羽球研究筆記'
CATALOG_CSV = SRC / '學術/近五年羽毛球文獻_2021-2026/文獻總目錄.csv'
LEARN_SRC = SRC / '教學'
TECH_SRC = SRC / '科技/2026羽球科技速覽.html'
SKILLS_SRC = SRC.parent / 'AVANCO_html/.codex/skills'
CONFIG = ROOT / 'tools/site_config.json'
LOG = ROOT / 'tools/updates_log.json'
CARDS = ROOT / 'tools/reading_cards.json'
WORKFLOW_SRC = SRC.parent.parent / 'AI瓦基第二大腦_專案包全集/E-學習筆記'
TZ = ZoneInfo('Asia/Macau')

# ---------------------------------------------------------------- 共用樣式

CSS = r"""
:root{--nav:#11241f;--nav-ink:#e8f2ec;--bg:#f4f6f2;--card:#fff;--ink:#16302a;--muted:#5d726b;--line:#d8e2dd;--brand:#0f5a46;--brand-ink:#fff;--accent:#d7f24b;--link:#0a6f8c;--code:#eef3f0;
--blue:#2563eb;--purple:#7c3aed;--green:#15803d;--orange:#c2410c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1714;--card:#17221e;--ink:#e3ede8;--muted:#9db1a9;--line:#2a3a34;--brand:#3fae8c;--brand-ink:#08130f;--accent:#b7d43a;--link:#6cc6e0;--code:#1f2d28}}
:root[data-theme="dark"]{--bg:#0f1714;--card:#17221e;--ink:#e3ede8;--muted:#9db1a9;--line:#2a3a34;--brand:#3fae8c;--brand-ink:#08130f;--accent:#b7d43a;--link:#6cc6e0;--code:#1f2d28}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif;overflow-wrap:anywhere}
a{color:var(--link)}
.top{position:sticky;top:0;z-index:5;background:var(--nav);color:var(--nav-ink);display:flex;gap:2px;align-items:center;overflow-x:auto;padding:6px 10px;white-space:nowrap;box-shadow:0 1px 0 rgba(0,0,0,.25)}
.top .brand{color:#d7f24b;font-weight:800;letter-spacing:.02em;padding:8px 10px 8px 4px;text-decoration:none}
.top a{color:var(--nav-ink);text-decoration:none;padding:8px 12px;border-radius:999px;font-size:15px}
.top a:hover{background:rgba(255,255,255,.1)}
.top a.on{background:#d7f24b;color:#16302a;font-weight:700}
.top button{margin-left:auto;border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:7px 12px;background:transparent;color:var(--nav-ink);font:inherit;font-size:14px;cursor:pointer}
main{max-width:920px;margin:auto;padding:24px 16px 64px}
.crumb{font-size:14px;color:var(--muted)}
h1{font-size:clamp(28px,6.4vw,42px);line-height:1.22;margin:.35em 0;font-weight:850;letter-spacing:-.01em}
h2{font-size:clamp(20px,4.6vw,24px);margin-top:1.9em;font-weight:800;letter-spacing:-.005em}
main>h2::after,.rc~h2::after{content:"";display:block;width:40px;height:4px;border-radius:2px;background:var(--accent);margin-top:8px}
.meta{font-size:14px;color:var(--muted);margin:-.2em 0 .6em}
.grid.home{grid-template-columns:repeat(auto-fill,minmax(min(380px,100%),1fr))}
.card.cat{border-top:5px solid hsl(var(--h) 55% 42%)}
.card.cat .tag{background:hsl(var(--h) 55% 42% / .12);color:hsl(var(--h) 55% 30%)}
.card .q{font-size:14px;color:var(--muted);margin:.1em 0 .4em}
h3{font-size:18px;margin-top:1.4em}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin:14px 0}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr))}
.tag{display:inline-block;font-size:13px;padding:2px 10px;border-radius:999px;background:var(--code);color:var(--muted);margin-right:6px}
mark,.hl{background:var(--accent);color:#16302a;padding:0 3px;border-radius:3px}
small,.muted{color:var(--muted)}
img{max-width:100%;height:auto;border-radius:10px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:15px;background:var(--card)}
th,td{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}
th{background:var(--code)}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.92em}
pre{background:var(--code);padding:12px;border-radius:10px;overflow-x:auto}
pre code{padding:0}
blockquote{margin:14px 0;padding:6px 16px;border-left:4px solid var(--line);color:var(--muted)}
.callout{border:1px solid var(--line);border-left:6px solid var(--brand);border-radius:12px;padding:6px 16px;margin:16px 0;background:var(--card)}
.callout-title{font-weight:700;margin:8px 0 4px}
.callout.warning,.callout.important{border-left-color:var(--orange)}
.callout.question{border-left-color:var(--purple)}
.callout.info,.callout.note,.callout.abstract,.callout.summary{border-left-color:var(--blue)}
.callout.tip{border-left-color:var(--green)}
.big a{display:inline-block;margin-top:6px;padding:10px 16px;border-radius:999px;background:var(--brand);color:var(--brand-ink);text-decoration:none;font-weight:600}
footer{margin-top:48px;font-size:14px;color:var(--muted)}
.hero{position:relative;overflow:hidden;border-radius:22px;margin:4px 0 18px;min-height:clamp(380px,62vh,500px);display:flex;align-items:flex-start;
 background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.16),transparent 38%),radial-gradient(circle at 82% 18%,rgba(125,211,252,.14),transparent 34%),linear-gradient(135deg,#fffefa,#f3f6f2);border:1px solid var(--line)}
.hero.band{min-height:clamp(230px,32vh,280px)}
.court-canvas{position:absolute;inset:0;z-index:0}
.court-canvas canvas{display:block;width:100%!important;height:100%!important}
.hero-text{position:relative;z-index:1;margin:16px;padding:14px 18px;border-radius:16px;background:color-mix(in srgb,var(--card) 70%,transparent);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);max-width:560px}
.hero-text h1{margin:.1em 0 .2em}.hero-text p{margin:.3em 0}
.hero-tip{font-size:13px;color:var(--muted)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hero{background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.18),transparent 38%),radial-gradient(circle at 82% 18%,rgba(59,130,246,.16),transparent 34%),linear-gradient(135deg,#0d1a16,#0f1714)}}
:root[data-theme="dark"] .hero{background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.18),transparent 38%),radial-gradient(circle at 82% 18%,rgba(59,130,246,.16),transparent 34%),linear-gradient(135deg,#0d1a16,#0f1714)}
@media (max-width:640px){
 table.cards,table.cards tbody,table.cards tr,table.cards td{display:block;width:100%}
 table.cards thead{display:none}
 table.cards tr{border:1px solid var(--line);border-radius:12px;margin:10px 0;padding:6px 10px;background:var(--card)}
 table.cards td{border:0;border-bottom:1px dashed var(--line);padding:6px 0}
 table.cards td:last-child{border-bottom:0}
 table.cards td[data-label]::before{content:attr(data-label);display:block;font-size:13px;color:var(--muted);font-weight:600}
}
"""

JS = r"""<script>
(function(){var r=document.documentElement,b=document.getElementById('theme');
function cur(){return r.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}
try{var s=localStorage.getItem('theme');if(s)r.dataset.theme=s}catch(e){}
function label(){if(b)b.textContent=cur()==='dark'?'☀️ 淺色':'🌙 深色'}
label();if(b)b.onclick=function(){r.dataset.theme=cur()==='dark'?'light':'dark';try{localStorage.setItem('theme',r.dataset.theme)}catch(e){}label()};
document.querySelectorAll('table').forEach(function(t){var h=[].map.call(t.querySelectorAll('thead th'),function(x){return x.textContent.trim()});
if(!h.length)return;t.classList.add('cards');t.querySelectorAll('tbody tr').forEach(function(tr){[].forEach.call(tr.children,function(td,i){if(h[i])td.setAttribute('data-label',h[i])})})});
})();
</script>"""

CAT_HUE = {'learn': 150, 'technology': 215, 'research': 270, 'skills': 25}   # 分類色：墨綠、藍、紫、橙

NAV = [('首頁', ''), ('學生學習', 'learn/'), ('教練科技', 'technology/'), ('教練研究', 'research/'),
       ('工具說明', 'skills/'), ('閱讀方法', 'guide/'), ('更新紀錄', 'updates/')]


def page(title: str, body: str, depth: int, active: str = '', desc: str = '') -> str:
    up = '../' * depth
    court_js = (f'\n<script src="{up}assets/vendor/p5.min.js" defer></script>\n<script src="{up}assets/court.js" defer></script>'
                if 'data-court=' in body else '')
    nav = f'<a class="brand" href="{up}">badminton</a>' + ''.join(f'<a href="{up}{href}"{" class=\"on\"" if href == active else ""}>{name}</a>' for name, href in NAV[1:])
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc or title)}">
<style>{CSS}</style>
</head>
<body>
<nav class="top" aria-label="網站導覽">{nav}<button id="theme" type="button">🌙 深色</button></nav>
<main>
{body}
<footer>badminton · 小選手，大目標 · <a href="{up}">回首頁</a></footer>
</main>
{JS}{court_js}
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(s or '')


def today() -> str:
    return dt.datetime.now(TZ).date().isoformat()


def zh_date(d: str) -> str:
    y, m, dd = d.split('-')
    return f'{int(y)} 年 {int(m)} 月 {int(dd)} 日'


def sha(paths) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- 研究筆記

TS = re.compile(r'_(\d{12})$')
SKIP_NOTES = {'index'}


def base_name(stem: str) -> str:
    return TS.sub('', stem)


def latest_notes() -> dict[str, Path]:
    """同名筆記只保留時間戳記最新的一份。"""
    chosen: dict[str, Path] = {}
    for p in sorted(NOTES.glob('*.md')):
        b = base_name(p.stem)
        if b in SKIP_NOTES:
            continue
        if b not in chosen or p.stem > chosen[b].stem:
            chosen[b] = p
    return chosen


def read_front(text: str):
    meta = {}
    if text.startswith('---\n'):
        end = text.find('\n---', 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ':' in line and not line.startswith(' '):
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip().strip('"')
            text = text[end + 4:].lstrip('\n')
    return meta, text


def gfm_id(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[^\w\- ]', '', s)
    return s.replace(' ', '-')


CALLOUT_ICON = {'tip': '💡', 'warning': '⚠️', 'important': '❗', 'question': '❓', 'info': 'ℹ️',
                'note': '📝', 'summary': '📌', 'abstract': '📌'}


def convert_callouts(text: str) -> str:
    out, lines, i = [], text.split('\n'), 0
    while i < len(lines):
        m = re.match(r'^>\s*\[!(\w+)\]([+-]?)\s*(.*)$', lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        kind = m.group(1).lower()
        title = m.group(3).strip() or kind
        body = []
        i += 1
        while i < len(lines) and lines[i].startswith('>'):
            body.append(re.sub(r'^>\s?', '', lines[i])); i += 1
        out += ['', f'<div class="callout {esc(kind)}">', f'<p class="callout-title">{CALLOUT_ICON.get(kind, "📝")} {esc(title)}</p>', '',
                *body, '', '</div>', '']
    return '\n'.join(out)


def convert_wikilinks(text: str, slugs: dict[str, str]) -> str:
    def rep(m):
        inner = m.group(1).replace('\\|', '|')
        target, _, label = inner.partition('|')
        target, _, anchor = target.partition('#')
        label = label.strip() or (anchor or base_name(target)).strip()
        target = target.strip()
        if not target:                                     # 同頁標題
            return f'[{label}](#{gfm_id(anchor)})'
        key = base_name(Path(target).stem if target.endswith('.md') else target)
        if key in slugs:
            href = slugs[key] + (f'#{gfm_id(anchor)}' if anchor else '')
            return f'[{label}]({href})'
        return label                                        # PDF 或未公開檔案：只留文字
    return re.sub(r'\[\[([^\]]+?)\]\]', rep, text)


def md_to_html(md: str) -> str:
    r = subprocess.run(['pandoc', '-f', 'gfm+yaml_metadata_block', '-t', 'html5', '--wrap=none'],
                       input=md, capture_output=True, text=True, check=True)
    return r.stdout


def note_group(b: str) -> str:
    if b.startswith('圖解'):
        return 'graphic'
    if re.match(r'^\d\d_', b):
        return 'chapter'
    return 'other'


def build_research(date: str, force: bool) -> list[str]:
    notes = latest_notes()
    images = [p for p in NOTES.glob('圖_*/*') if p.is_file()]
    digest = sha(list(notes.values()) + images + [NOTES / 'index.md', CATALOG_CSV])
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    issues = cfg['categories']['research']['issues']
    if issues and issues[0].get('source_hash') == digest and not force:
        return []
    out = ROOT / f'research/badminton-{date}'
    if out.exists():
        shutil.rmtree(out)
    (out / '圖片').mkdir(parents=True)
    (out / '資料').mkdir()
    for p in images:
        dest = out / '圖片' / p.parent.name / p.name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(p, dest)

    slugs = {b: f'{b}.html' for b in notes}
    slugs['index'] = 'index.html'
    entries = []

    def render(md_text: str) -> str:
        md_text = convert_callouts(md_text)
        md_text = convert_wikilinks(md_text, slugs)
        md_text = re.sub(r'\]\((圖_[^)]+)\)', r'](圖片/\1)', md_text)
        md_text = re.sub(r'\]\(([^)/#]+?)\.md(#[^)]*)?\)', lambda m: f'](' + slugs.get(base_name(m.group(1)), '00_羽球研究總覽.html') + (m.group(2) or '') + ')', md_text)
        md_text = md_text.replace('(Europe/Rome)', '').replace('/Users/', '')
        return md_to_html(md_text)

    for b, p in sorted(notes.items()):
        meta, text = read_front(p.read_text(encoding='utf-8'))
        title = meta.get('title') or (re.search(r'^# (.+)$', text, re.M) or [None, b])[1]
        desc = meta.get('description', '')
        note_html = render(text)
        mline = f'<p class="meta">教練研究 · 整理日期 {esc(meta.get("date", ""))} · 依原研究整理，不是原文全文</p>'
        k = note_html.find('</h1>')
        note_html = note_html[:k + 5] + mline + note_html[k + 5:] if k != -1 else mline + note_html
        body = (f'<p class="crumb"><a href="../">教練研究</a> › <a href="index.html">本期目錄</a></p>'
                + note_html +
                '<p class="big"><a href="index.html">回本期目錄</a></p>')
        (out / slugs[b]).write_text(page(f'{title}｜教練研究', body, 2, 'research/', desc), encoding='utf-8')
        q = (load_cards().get('research:' + b) or {}).get('question', '')
        entries.append({'slug': slugs[b], 'title': title, 'desc': desc, 'group': note_group(b), 'q': q})

    n_rows = build_catalog(out)

    meta, idx_text = read_front((NOTES / 'index.md').read_text(encoding='utf-8'))
    groups = [('chapter', '研究章節（完整版）', '每章整理一個主題的研究、證據強弱與教練應用。'),
              ('graphic', '圖解版（先看這裡）', '用動畫、圖表和數字講一個問題，5 分鐘看完。'),
              ('other', '附錄與紀錄', '課堂筆記、書單與文獻整理過程。')]
    lists = ''
    for g, gt, gd in groups:
        items = ''.join(f'<li><a href="{e["slug"]}">{esc(e["title"])}</a>' + (f'<br><small>這篇回答：{esc(e["q"])}</small>' if e.get('q') else (f'<br><small>{esc(e["desc"])}</small>' if e['desc'] else '')) + '</li>'
                        for e in entries if e['group'] == g)
        lists += f'<h2>{gt}</h2><p class="muted">{gd}</p><ul>{items}</ul>'
    body = (f'<p class="crumb"><a href="../">教練研究</a> › {zh_date(date)}</p>'
            f'<div class="card"><small>教練研究 · 給教練 · {zh_date(date)} 更新</small>'
            f'<p>本期共 <b>{len(entries)}</b> 篇整理、<b>{n_rows:,}</b> 筆文獻目錄。內容由本機研究筆記自動轉成網頁；論文全文因版權與檔案大小不上傳，請用各篇的 DOI（論文的固定網址）連到原出處。</p>'
            f'<p class="big"><a href="文獻目錄.html">搜尋 {n_rows:,} 筆文獻目錄</a></p></div>'
            + render(idx_text) + lists)
    (out / 'index.html').write_text(page(f'教練研究 {date}｜羽球研究筆記', body, 2, 'research/', meta.get('description', '')), encoding='utf-8')

    issue = {'date': date, 'path': f'research/badminton-{date}/', 'title': '羽球研究筆記：用數據看懂羽球',
             'summary': f'{len(entries)} 篇研究整理與圖解（多球、戰術、敏捷、肌力、心理、傷病、CLA 等），附 {n_rows:,} 筆近五年文獻目錄。',
             'source_hash': digest}
    cfg['categories']['research']['issues'] = [issue] + [i for i in issues if i['date'] != date]
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return [f'教練研究新增一期：{len(entries)} 篇整理、{n_rows:,} 筆文獻目錄（research/badminton-{date}/）']


CATALOG_FIELDS = [('id', 'id'), ('發表日期', 'date'), ('標題', 'title'), ('作者', 'authors'), ('地區', 'region'),
                  ('初步主題', 'topic'), ('來源', 'source'), ('DOI', 'doi'), ('來源網址', 'url'), ('開放取用', 'oa'), ('引用次數', 'cites')]


def build_catalog(out: Path) -> int:
    rows = []
    with CATALOG_CSV.open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            rows.append({k2: (r.get(k1) or '').strip() for k1, k2 in CATALOG_FIELDS})
    rows.sort(key=lambda r: r['date'], reverse=True)
    (out / '資料/文獻總目錄.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    topics = sorted({r['topic'] for r in rows if r['topic']})
    opts = ''.join(f'<option>{esc(t)}</option>' for t in topics)
    body = f"""<p class="crumb"><a href="../">教練研究</a> › <a href="index.html">本期目錄</a> › 文獻目錄</p>
<h1>近五年羽毛球文獻目錄</h1>
<div class="card"><p>共 <b>{len(rows):,}</b> 筆（發表日期 2021-10 至 2026-10，OpenAlex 等資料庫檢索後初步分類）。這裡只列題名與出處，<mark>「初步主題」是自動分類，還沒全部人工核對</mark>。</p>
<p class="muted">用法：在下面的搜尋框輸入關鍵字（中文或英文，例如「多球」「smash」「injury」），或選一個主題，清單會立即更新。按標題會開到論文原出處。</p></div>
<div class="card" style="display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr))">
<label>關鍵字<br><input id="q" type="search" placeholder="例如：smash、多球、傷害" style="width:100%;padding:10px;font:inherit;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink)"></label>
<label>主題<br><select id="t" style="width:100%;padding:10px;font:inherit;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink)"><option value="">全部主題</option>{opts}</select></label>
<label><input id="oa" type="checkbox"> 只看可免費下載全文（開放取用）</label>
</div>
<p id="count" class="muted">載入中…</p>
<div id="list"></div>
<p><button id="more" type="button" style="padding:10px 16px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit">顯示更多</button></p>
<script>
(function(){{var all=[],shown=50,$=function(i){{return document.getElementById(i)}};
function e(s){{return String(s||'').replace(/[&<>"]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}})}}
function draw(){{var q=$('q').value.trim().toLowerCase(),t=$('t').value,oa=$('oa').checked;
var r=all.filter(function(x){{return(!t||x.topic===t)&&(!oa||x.oa==='是')&&(!q||(x.title+' '+x.authors+' '+x.source).toLowerCase().indexOf(q)>-1)}});
$('count').textContent='找到 '+r.length.toLocaleString()+' 筆'+(r.length>shown?'，先顯示 '+shown+' 筆':'');
$('list').innerHTML=r.slice(0,shown).map(function(x){{var u=x.doi||x.url;return '<div class="card"><small>'+e(x.date)+' · '+e(x.region)+' · '+e(x.topic)+(x.oa==='是'?' · 開放取用':'')+(x.cites?' · 被引用 '+e(x.cites)+' 次':'')+'</small><br>'+(u?'<a hre'+'f="'+e(u)+'" target="_blank" rel="noopener">'+e(x.title)+'</a>':e(x.title))+'<br><small>'+e(x.authors.split('; ').slice(0,4).join('、'))+(x.authors.split('; ').length>4?' 等':'')+' · '+e(x.source)+'</small></div>'}}).join('');
$('more').style.display=r.length>shown?'':'none'}}
['q','t','oa'].forEach(function(i){{$(i).addEventListener('input',function(){{shown=50;draw()}})}});
$('more').onclick=function(){{shown+=50;draw()}};
fetch('資料/文獻總目錄.json').then(function(r){{return r.json()}}).then(function(d){{all=d;draw()}}).catch(function(){{$('count').textContent='目錄載入失敗，請重新整理頁面。'}});
}})();
</script>"""
    (out / '文獻目錄.html').write_text(page('近五年羽毛球文獻目錄｜教練研究', body, 2, 'research/'), encoding='utf-8')
    return len(rows)


# ---------------------------------------------------------------- 本機來源同步

def same(src: Path, pub: Path) -> bool:
    """比較本機來源與網站副本；網頁和 Markdown 先去掉自動插入的閱讀卡與導覽條。"""
    if pub.suffix in ('.html', '.md'):
        return src.read_text(encoding='utf-8') == RC.strip(pub.read_text(encoding='utf-8'))
    return filecmp.cmp(src, pub, shallow=False)


def sync_sources() -> list[str]:
    notes = []
    # 教練科技：本機來源 → 網站副本
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    tech = cfg['categories']['technology']['issues'][0]
    dest = ROOT / tech['path'] / 'index.html'
    if TECH_SRC.exists() and not same(TECH_SRC, dest):
        shutil.copy2(TECH_SRC, dest)
        notes.append('教練科技：已從本機來源同步最新內容')
    # 學生學習：只同步網站已有的檔案（index.html 是網站專用入口，不覆蓋）
    for issue in cfg['categories']['learn']['issues']:
        src_dir = issue.get('source') and SRC / issue['source']
        if not src_dir or not src_dir.exists():
            continue
        pub = ROOT / issue['path']
        changed = 0
        for f in pub.rglob('*'):
            rel = f.relative_to(pub)
            if not f.is_file() or rel.as_posix() == 'index.html':
                continue
            s = src_dir / rel
            if s.exists() and not same(s, f):
                shutil.copy2(s, f); changed += 1
        if changed:
            notes.append(f'學生學習 {issue["date"]}：從本機來源同步 {changed} 個檔案')
    # 新的月報資料夾：需要人工整理與影片權限核對，不自動發佈
    known = {i.get('source') for i in cfg['categories']['learn']['issues']} | set(cfg.get('ignored_sources', []))
    for d in sorted(LEARN_SRC.glob('YouTube月報_*')):
        rel = d.relative_to(SRC).as_posix()
        if rel not in known:
            notes.append(f'待整理：發現新的教學來源「{rel}」，學生頁須先核對影片可免費觀看，才可發佈')
    # 工具說明：skill 有改動時提醒人工更新說明頁
    if SKILLS_SRC.exists():
        h = sha(list(SKILLS_SRC.glob('*/SKILL.md')))
        if h != cfg['categories']['skills']['issues'][0].get('source_hash'):
            notes.append('待整理：AVANCO skill 原檔有改動，工具說明頁需要人工更新（不自動公開設定細節）')
    return notes


# ---------------------------------------------------------------- 閱讀卡（閱讀與記憶工作流）

_CARDS = None


def load_cards() -> dict:
    global _CARDS
    if _CARDS is None:
        raw = json.loads(CARDS.read_text(encoding='utf-8')) if CARDS.exists() else {}
        raw.pop('_說明', None)
        _CARDS = {k: (raw[v['same_as']] if 'same_as' in v else v) for k, v in raw.items()}
    return _CARDS


def put_site_strip(text: str, up: str, here: str) -> str:
    text = re.sub(re.escape(RC.SITE_START) + r'.*?' + re.escape(RC.SITE_END), '', text, flags=re.S)
    if '<nav class="top" aria-label="網站導覽">' in text:   # 已用本站統一外框，不需要
        return text
    bar = RC.site_strip(up, here)
    m = re.search(r'<body[^>]*>', text)
    if m:
        return text[:m.end()] + bar + text[m.end():]
    i = text.find('<main')
    return text[:i] + bar + text[i:] if i != -1 else bar + text


def inject_cards(cfg: dict) -> tuple[int, list[str]]:
    """把閱讀卡放進每篇文章（研究頁只放最新一期）。回傳（放入篇數，缺卡的研究筆記）。"""
    cards = load_cards()
    rissue = cfg['categories']['research']['issues']
    rdir = ROOT / rissue[0]['path'] if rissue else None
    n = 0
    for key, card in cards.items():
        if key.startswith('research:'):
            if not rdir:
                continue
            target, up = rdir / (key.split(':', 1)[1] + '.html'), '../../'
        else:
            target, up = ROOT / key, '../' * key.count('/')
        if not target.exists():
            continue
        t = target.read_text(encoding='utf-8')
        new = RC.insert(t, RC.block(card, key, up + 'guide/'))
        new = put_site_strip(new, up, target.relative_to(ROOT).parts[0] + '/')
        if new != t:
            target.write_text(new, encoding='utf-8')
        n += 1
    missing = []
    if rdir:
        for f in sorted(rdir.glob('*.html')):
            if f.stem not in ('index', '文獻目錄') and f'research:{f.stem}' not in cards:
                missing.append(f.stem)
    return n, missing


def build_guide():
    """閱讀方法頁：直接由使用者的〈閱讀與記憶工作流〉原檔產生，原檔更新時每週自動跟著更新。"""
    srcs = sorted(WORKFLOW_SRC.glob('閱讀與記憶工作流_*.md')) if WORKFLOW_SRC.exists() else []
    out = ROOT / 'guide'
    out.mkdir(exist_ok=True)
    if srcs:
        shutil.copy2(srcs[-1], out / '閱讀與記憶工作流.md')
    md = (out / '閱讀與記憶工作流.md').read_text(encoding='utf-8') if (out / '閱讀與記憶工作流.md').exists() else '# 閱讀與記憶工作流'
    md = md.split('\n', 1)[1] if md.startswith('# ') else md
    body_md = md_to_html(convert_callouts(md))
    body = f"""<p class="crumb"><a href="../">首頁</a> › 閱讀方法</p>
<h1>閱讀方法：先問一句，再選讀法</h1>
<p class="meta">全站每篇文章都用這套讀法 · 原文：<a href="閱讀與記憶工作流.md">閱讀與記憶工作流.md</a>（Markdown 文字檔）</p>
<div class="card"><h2 style="margin-top:.2em">在這個網站怎樣用？</h2>
<ol>
<li>打開任何一篇文章，最上面有一張<mark>閱讀卡</mark>，第一句寫著「我讀這篇是為了回答：……」。</li>
<li>按一個讀法：<b>查資料</b>、<b>做決定</b>或<b>日後要教或反覆用</b>。卡片會告訴你先讀哪裡、讀到哪裡可以停。</li>
<li>看四欄筆記：一句話核心、關鍵數據（最多 3 項，附出處）、因果／流程、跨域應用。</li>
<li>想長期記住的文章：打開「閉卷回想」，蓋住上面自己答兩題，再按「開始排複習」。隔天和第 7 天回來各答一次，每次 0–3 分。</li>
<li>按「複製成 Obsidian 筆記」，就能把整張卡貼進自己的 Obsidian（筆記軟體）。</li>
</ol>
<p class="muted">標示說明：<b>相關</b>＝原文只支持兩件事一起出現，不能當成因果；<b>機制未明</b>＝原文沒有交代為甚麼；<b>待驗證</b>＝超出原文、需要自己試過才知道。</p></div>
<h2>原文：閱讀與記憶工作流</h2>
{body_md}
<script>document.querySelectorAll('main pre').forEach(function(p){{var b=document.createElement('button');b.type='button';b.textContent='複製';b.style.cssText='float:right;margin:-4px -4px 6px 8px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-size:13px;cursor:pointer';b.onclick=function(){{var t=p.querySelector('code').textContent;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){{b.textContent='已複製 ✓'}},function(){{b.textContent='請手動選取'}})}};p.prepend(b)}})</script>"""
    (out / 'index.html').write_text(page('閱讀方法｜badminton', body, 1, 'guide/', '全站文章使用的閱讀與記憶工作流。'), encoding='utf-8')


# ---------------------------------------------------------------- 目錄頁

def build_indexes(cfg: dict, log: list[dict]):
    cats = cfg['categories']
    # 分類目錄
    for key, c in cats.items():
        cards = ''
        for i, it in enumerate(c['issues']):
            rel = it['path'].split('/', 1)[1]
            extra = ''.join(f' · <a href="{rel}{href}">{esc(t)}</a>' for t, href in it.get('extra', []))
            cards += (f'<article class="card cat" style="--h:{CAT_HUE.get(key, 160)}"><small>{zh_date(it["date"])}{" · 最新" if i == 0 else ""}</small>'
                      f'<h3><a href="{rel}">{esc(it["title"])}</a></h3><p>{esc(it["summary"])}</p>'
                      f'<p><a href="{rel}">打開這一期 →</a>{extra}</p></article>')
        ext = ''.join(f'<article class="card"><small>{esc(x["note"])}</small><h3><a href="{esc(x["url"])}">{esc(x["title"])}</a></h3><p>{esc(x["summary"])}</p></article>'
                      for x in c.get('external', []))
        body = (f'<p class="crumb"><a href="../">首頁</a> › {esc(c["name"])}</p>'
                f'<section class="hero band" data-court="mono" data-hue="{CAT_HUE.get(key, 160)}"><div class="hero-text"><h1>{esc(c["name"])}</h1>'
                f'<p><span class="tag">{esc(c["audience"])}</span></p></div></section><p>{esc(c["intro"])}</p>'
                f'<p class="muted">每一期按日期排列，最新的在最上面。</p>{cards}{ext}')
        (ROOT / key).mkdir(exist_ok=True)
        (ROOT / key / 'index.html').write_text(page(f'{c["name"]}｜badminton', body, 1, f'{key}/', c['intro']), encoding='utf-8')

    # 更新紀錄
    items = ''
    for e in log:
        lis = ''.join(f'<li>{esc(x)}</li>' for x in e['items']) or '<li>本週本機資料沒有變動，網站內容維持不變。</li>'
        items += f'<article class="card"><small>{esc(e.get("kind", "每週自動更新"))}</small><h3>{zh_date(e["date"])}</h3><ul>{lis}</ul></article>'
    body = ('<p class="crumb"><a href="../">首頁</a> › 更新紀錄</p><h1>更新紀錄</h1>'
            '<p>網站每星期六早上 8 點（澳門時間）自動檢查本機資料：有新的研究筆記就新增一期，教學與科技來源有修改就同步，'
            '再檢查連結並發佈。需要人手核對的內容（例如新影片是否免費）會列為「待整理」，不會自動放上學生頁。</p>' + items)
    (ROOT / 'updates').mkdir(exist_ok=True)
    (ROOT / 'updates/index.html').write_text(page('更新紀錄｜badminton', body, 1, 'updates/'), encoding='utf-8')

    # 首頁
    order = ['learn', 'technology', 'research', 'skills']
    cards = ''
    for key in order:
        c = cats[key]
        it = c['issues'][0]
        cards += (f'<article class="card cat" style="--h:{CAT_HUE.get(key, 160)}"><span class="tag">{esc(c["audience"])}</span><small>最新 {it["date"]}</small>'
                  f'<h2 style="margin-top:.4em">{esc(c["name"])}</h2><p>{esc(c["intro"])}</p>'
                  f'<p><b>{esc(it["title"])}</b><br><small>{esc(it["summary"])}</small></p>'
                  f'<p class="big"><a href="{it["path"]}">打開最新一期</a></p><p><a href="{key}/">看全部 {len(c["issues"])} 期 →</a></p></article>')
    last = log[0] if log else {'date': today(), 'items': []}
    upd = ''.join(f'<li>{esc(x)}</li>' for x in last['items'][:4]) or '<li>本週本機資料沒有變動。</li>'
    body = f"""<section class="hero" data-court="rally"><div class="hero-text"><h1>小選手，大目標。</h1>
<p>羽球學習與教練資料站：學生從細節開始練，教練用研究和科技安排訓練。</p>
<p class="hero-tip">背景是自動對打的 3D 羽球場；點一下球場空白處，就會朝那裡殺球。</p></div></section>
<div class="grid home">{cards}</div>
<article class="card"><small>閱讀方法</small><h2 style="margin-top:.4em">每篇文章都有一張閱讀卡</h2><p>先寫一句「我讀這篇是為了回答甚麼」，再選查資料、做決定或日後要教的讀法；四欄筆記和閉卷回想幫你真的記住。</p><p><a href="guide/">看閱讀方法 →</a></p></article>
<article class="card"><small>每星期六早上 8 點自動更新</small><h2 style="margin-top:.4em">最近更新：{zh_date(last['date'])}</h2><ul>{upd}</ul><p><a href="updates/">看全部更新紀錄 →</a></p></article>
<article class="card"><small>另一個網站</small><h2 style="margin-top:.4em">手指發力 3D 互動教學</h2><p>用 3D 手骨模型看手指怎樣用力，5 個步驟配旁白。</p><p class="big"><a href="https://winglao.github.io/badminton-finger-biomechanics/">打開 3D 教學</a></p></article>
<p class="muted">學生頁推薦的影片都核對過可免費觀看，不需要會員或信用卡。<a href="learn/badminton-2026-11-15/影片免費觀看檢查_20261115.html">查看核對表</a></p>"""
    (ROOT / 'index.html').write_text(page('badminton｜小選手，大目標', body, 0, ''), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=today())
    ap.add_argument('--force-research', action='store_true')
    ap.add_argument('--kind', default='每週自動更新')
    ap.add_argument('--note', action='append', default=[], help='額外寫入本次更新紀錄的一句說明')
    a = ap.parse_args()
    items = list(a.note)
    items += build_research(a.date, a.force_research)
    items += sync_sources()
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    n_cards, missing = inject_cards(cfg)
    if missing:
        items.append('待整理：這些研究筆記還沒有閱讀卡（請在 tools/reading_cards.json 補上）：' + '、'.join(missing))
    build_guide()
    log = json.loads(LOG.read_text(encoding='utf-8')) if LOG.exists() else []
    # 同一天重跑：保留之前寫入的項目，再加上新項目（不重複）
    old = next((e for e in log if e['date'] == a.date), None)
    if old:
        items = old['items'] + [x for x in items if x not in old['items']]
    log = [e for e in log if e['date'] != a.date]
    log.insert(0, {'date': a.date, 'kind': old['kind'] if old else a.kind, 'items': items})
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    build_indexes(cfg, log)
    print(json.dumps({'date': a.date, 'items': items}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.exit(main())
