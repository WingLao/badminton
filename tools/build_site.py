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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading_card as RC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]          # 網站 Git 儲存庫（~/Projects/badminton，不放在 iCloud 同步資料夾）
# 本機資料來源（研究筆記、教學、科技）仍在 iCloud 桌面；建站只「讀取」，不寫入。可用環境變數 BADMINTON_SRC 改位置。
SRC = Path(os.environ.get('BADMINTON_SRC', Path.home() / 'Desktop/Badminton/網站資料')).expanduser()
NOTES = SRC / '學術/羽球研究筆記'
CATALOG_CSV = SRC / '學術/近五年羽毛球文獻_2021-2026/文獻總目錄.csv'
# 學術資料夾中其他研究文件（P39：要放進網站）；PDF 原文不上傳，只保留題名與原出處
EXTRA_DOCS = ['學術/男子雙打認知教學運用.md', '學術/羽毛球近五年文獻整理.md', '學術/研究紀錄.md',
              '學術/近五年羽毛球文獻_2021-2026/請先閱讀.md', '學術/近五年羽毛球文獻_2021-2026/多球訓練研究統整_2025.md',
              '學術/羽球研究筆記/課堂延伸研究原文/00_原文索引_*.md', '學術/羽球研究筆記/文獻候選索引/*.md']
MATCH_XLSX = SRC / '學術/鄭任佑'
NEWS_SRC = SRC / '學術/每週新文獻'      # badminton-weekly-papers skill 每週五產生
VIDEO_SRC = SRC / '每週影片'            # badminton-weekly-videos skill 每週五產生
LEARN_SRC = SRC / '教學'
TECH_SRC = SRC / '科技/2026羽球科技速覽.html'
SKILLS_SRC = SRC.parent / 'AVANCO_html/.codex/skills'
CONFIG = ROOT / 'tools/site_config.json'
LOG = ROOT / 'tools/updates_log.json'
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
.hero{position:relative;overflow:hidden;border-radius:22px;margin:4px 0 18px;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);align-items:center;gap:0;
 background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.16),transparent 38%),radial-gradient(circle at 82% 18%,rgba(125,211,252,.14),transparent 34%),linear-gradient(135deg,#fffefa,#f3f6f2);border:1px solid var(--line)}
.court-canvas{position:relative;order:2;height:clamp(200px,28vh,250px);z-index:0}
.hero.band .court-canvas{height:clamp(140px,18vh,170px)}
.court-canvas canvas{display:block;width:100%!important;height:100%!important}
.hero-text{position:relative;z-index:1;order:1;padding:18px 22px}
@media (max-width:640px){.hero{grid-template-columns:1fr}.court-canvas{height:130px}.hero.band .court-canvas{height:100px}.hero-text{padding:14px 16px 4px}}
.hero-text h1{margin:.1em 0 .2em}.hero-text p{margin:.3em 0}
.hero-tip{font-size:13px;color:var(--muted)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hero{background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.18),transparent 38%),radial-gradient(circle at 82% 18%,rgba(59,130,246,.16),transparent 34%),linear-gradient(135deg,#0d1a16,#0f1714)}}
:root[data-theme="dark"] .hero{background:radial-gradient(circle at 18% 12%,rgba(45,212,191,.18),transparent 38%),radial-gradient(circle at 82% 18%,rgba(59,130,246,.16),transparent 34%),linear-gradient(135deg,#0d1a16,#0f1714)}
table.wide{font-size:13px;white-space:nowrap}
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
document.querySelectorAll('table').forEach(function(t){if(t.classList.contains('wide'))return;var h=[].map.call(t.querySelectorAll('thead th'),function(x){return x.textContent.trim()});
if(!h.length)return;t.classList.add('cards');t.querySelectorAll('tbody tr').forEach(function(tr){[].forEach.call(tr.children,function(td,i){if(h[i])td.setAttribute('data-label',h[i])})})});
})();
</script>"""

CAT_HUE = {'learn': 150, 'technology': 215, 'research': 270, 'skills': 25, 'news': 45}   # 分類色：墨綠、藍、紫、橙

NAV = [('首頁', ''), ('最新消息', 'news/'), ('學生學習', 'learn/'), ('教練科技', 'technology/'), ('教練研究', 'research/'),
       ('工具說明', 'skills/'), ('更新紀錄', 'updates/')]


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
<meta name="robots" content="noindex, nofollow, noarchive">
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
    extras = extra_docs()
    xlsx = sorted(MATCH_XLSX.glob('*.xlsx')) if MATCH_XLSX.exists() else []
    digest = sha(list(notes.values()) + images + [NOTES / 'index.md', CATALOG_CSV] + [p for p, _ in extras] + xlsx)
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
        md_text = md_text.replace('(Europe/Rome)', '')
        md_text = re.sub(r'`?/Users/[^`\s)）]*`?', '（本機資料夾）', md_text)   # 不公開本機路徑與帳號名稱
        md_text = re.sub(r'\[([^\]]+)\]\((?!https?:|#|mailto:)[^)]+\.(?:pdf|PDF|csv|xlsx|jsonl|txt)\)', r'\1', md_text)   # 本機檔案連結改成純文字
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
        entries.append({'slug': slugs[b], 'title': title, 'desc': desc, 'group': note_group(b)})

    for p, slug in extras:
        meta, text = read_front(p.read_text(encoding='utf-8'))
        title = meta.get('title') or (re.search(r'^# (.+)$', text, re.M) or [None, slug])[1]
        note_html = render(text)
        rel = p.relative_to(SRC / '學術').parent.as_posix()
        mline = f'<p class="meta">研究文件 · 來源資料夾：學術/{esc(rel) if rel != "." else ""} · 論文 PDF 不上傳，請用原出處連結</p>'
        k = note_html.find('</h1>')
        note_html = note_html[:k + 5] + mline + note_html[k + 5:] if k != -1 else f'<h1>{esc(title)}</h1>' + mline + note_html
        body = f'<p class="crumb"><a href="../">教練研究</a> › <a href="index.html">本期目錄</a></p>{note_html}<p class="big"><a href="index.html">回本期目錄</a></p>'
        (out / f'{slug}.html').write_text(page(f'{title}｜教練研究', body, 2, 'research/', meta.get('description', '')), encoding='utf-8')
        entries.append({'slug': f'{slug}.html', 'title': title, 'desc': meta.get('description', ''), 'group': 'docs'})
    for e in build_match_data(out, xlsx):
        entries.append(e)

    n_rows = build_catalog(out)

    meta, idx_text = read_front((NOTES / 'index.md').read_text(encoding='utf-8'))
    groups = [('chapter', '研究章節（完整版）', '每章整理一個主題的研究、證據強弱與教練應用。'),
              ('graphic', '圖解版（先看這裡）', '用動畫、圖表和數字講一個問題，5 分鐘看完。'),
              ('docs', '研究文件', '學術資料夾中的文獻整理、男子雙打認知教學、研究紀錄與候選文獻清單。'),
              ('data', '比賽數據（Excel）', '奧運羽球比賽（鄭任佑整理）的逐拍紀錄、統計表與信度表；可下載原始 Excel。'),
              ('other', '附錄與紀錄', '課堂筆記、書單與文獻整理過程。')]
    lists = ''
    for g, gt, gd in groups:
        items = ''.join(f'<li><a href="{e["slug"]}">{esc(e["title"])}</a>' + (f'<br><small>{esc(e["desc"])}</small>' if e['desc'] else '') + '</li>'
                        for e in entries if e['group'] == g)
        lists += f'<h2>{gt}</h2><p class="muted">{gd}</p><ul>{items}</ul>'
    body = (f'<p class="crumb"><a href="../">教練研究</a> › {zh_date(date)}</p>'
            f'<div class="card"><small>教練研究 · 給教練 · {zh_date(date)} 更新</small>'
            f'<p>本期共 <b>{len(entries)}</b> 篇整理、<b>{n_rows:,}</b> 筆文獻目錄。內容由本機研究筆記自動轉成網頁；論文全文因版權與檔案大小不上傳，請用各篇的 DOI（論文的固定網址）連到原出處。</p>'
            f'<p class="big"><a href="文獻目錄.html">搜尋 {n_rows:,} 筆文獻目錄</a></p></div>'
            + render(idx_text) + lists)
    (out / 'index.html').write_text(page(f'教練研究 {date}｜羽球研究筆記', body, 2, 'research/', meta.get('description', '')), encoding='utf-8')

    issue = {'date': date, 'path': f'research/badminton-{date}/', 'title': '羽球研究筆記：用數據看懂羽球',
             'summary': f'{len(entries)} 篇研究整理、圖解、研究文件與比賽數據（多球、戰術、敏捷、肌力、心理、傷病、CLA 等），附 {n_rows:,} 筆近五年文獻目錄。',
             'source_hash': digest}
    cfg['categories']['research']['issues'] = [issue] + [i for i in issues if i['date'] != date]
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return [f'教練研究更新：{len(entries)} 篇（含研究文件 {sum(e["group"] == "docs" for e in entries)} 篇、比賽數據 {sum(e["group"] == "data" for e in entries)} 場）、{n_rows:,} 筆文獻目錄（research/badminton-{date}/）']


def extra_docs() -> list[tuple[Path, str]]:
    out = []
    for pat in EXTRA_DOCS:
        for p in sorted(SRC.glob(pat)):
            out.append((p, '文件_' + base_name(p.stem)))
    return out


def read_xlsx(path: Path) -> list[tuple[str, list[list[str]]]]:
    """只用 Python 內建模組讀 Excel（每週自動更新不必另裝套件）。回傳 [(工作表名稱, 列資料)]。"""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = []
    for sh in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', ns):
        target = rels[sh.get('{%s}id' % ns['r'])].lstrip('/')
        target = target if target.startswith('xl/') else 'xl/' + target
        grid = {}
        for c in ET.fromstring(z.read(target)).iter('{%s}c' % ns['m']):
            ref, t = c.get('r'), c.get('t')
            v = c.find('m:v', ns)
            if t == 's' and v is not None:
                val = shared[int(v.text)]
            elif t == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter('{%s}t' % ns['m']))
            elif v is not None and v.text is not None:
                val = v.text
                if t != 'str' and t != 'b':
                    try:
                        f = float(val)
                        val = str(int(f)) if f.is_integer() else f'{f:.3f}'.rstrip('0')
                    except ValueError:
                        pass
            else:
                continue
            m = re.match(r'([A-Z]+)(\d+)', ref)
            col = 0
            for ch in m.group(1):
                col = col * 26 + ord(ch) - 64
            grid[(int(m.group(2)), col)] = val.strip()
        if not grid:
            out.append((sh.get('name'), []))
            continue
        rows = sorted({r for r, _ in grid})
        cols = sorted({c for _, c in grid})
        table = [[grid.get((r, c), '') for c in cols] for r in rows]
        table = [row for row in table if any(row)]
        out.append((sh.get('name'), table))
    return out


def build_match_data(out: Path, files: list[Path]) -> list[dict]:
    entries = []
    if not files:
        return entries
    (out / '資料/比賽數據').mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, out / '資料/比賽數據' / f.name)
        sheets = read_xlsx(f)
        name = f.stem
        parts = ''
        for sname, rows in sheets:
            if not rows:
                continue
            head, rest = rows[0], rows[1:]
            th = ''.join(f'<th>{esc(x)}</th>' for x in head)
            tb = ''.join('<tr>' + ''.join(f'<td>{esc(x)}</td>' for x in r) + '</tr>' for r in rest)
            parts += (f'<details class="card"><summary><b>{esc(sname)}</b> <small>（{len(rest)} 列 × {len(head)} 欄）</small></summary>'
                      f'<div style="overflow-x:auto"><table class="wide"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div></details>')
        body = (f'<p class="crumb"><a href="../">教練研究</a> › <a href="index.html">本期目錄</a></p><h1>比賽數據：{esc(name)}</h1>'
                f'<p class="meta">研究文件 · 來源：學術/鄭任佑（Excel 原始檔）</p>'
                f'<div class="card"><p>每個工作表是一個表格，按標題打開。<b>list-reference</b> 是記錄時用的分類（主被動、主動技術、被動技術、情況、站位）；'
                f'<b>紀錄表</b> 是逐拍紀錄；<b>表格／工作表</b> 是樞紐統計；<b>信度</b> 是兩位記錄者的一致性核對。空白列已略去。</p>'
                f'<p class="big"><a href="資料/比賽數據/{esc(f.name)}" download>下載原始 Excel</a></p></div>{parts}'
                f'<p class="big"><a href="index.html">回本期目錄</a></p>')
        slug = '數據_' + name
        (out / f'{slug}.html').write_text(page(f'比賽數據：{name}｜教練研究', body, 2, 'research/'), encoding='utf-8')
        entries.append({'slug': f'{slug}.html', 'title': f'比賽數據：{name}', 'desc': f'{len([1 for _, r in sheets if r])} 個工作表；逐拍紀錄與統計', 'group': 'data'})
    return entries


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
        return src.read_text(encoding='utf-8') == RC.strip(pub.read_text(encoding='utf-8')).replace(NOINDEX, '')
    return filecmp.cmp(src, pub, shallow=False)


def sync_sources() -> list[str]:
    notes = []
    # 教練科技：本機來源 → 網站副本
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    # 只同步到來源是〈2026羽球科技速覽〉的那一期（不一定是最新一期；其他期是手寫或自動產生的頁面）
    rel_src = TECH_SRC.relative_to(SRC).as_posix()
    tech = next((i for i in cfg['categories']['technology']['issues'] if i.get('source') == rel_src), None)
    dest = ROOT / tech['path'] / 'index.html' if tech else None
    if dest and TECH_SRC.exists() and not same(TECH_SRC, dest):
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

NOINDEX = '<meta name="robots" content="noindex, nofollow, noarchive">'


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


def put_noindex(text: str) -> str:
    """不讓搜尋引擎收錄：每頁加 robots meta（GitHub Pages 專案網站的 robots.txt 不會生效）。"""
    if NOINDEX in text:
        return text
    m = re.search(r'<meta charset[^>]*>', text, flags=re.I)
    if m:
        return text[:m.end()] + NOINDEX + text[m.end():]
    m = re.search(r'<head[^>]*>', text, flags=re.I)
    return text[:m.end()] + NOINDEX + text[m.end():] if m else NOINDEX + text


def tidy_hand_pages():
    """手寫及舊版頁面：移除舊閱讀卡、加網站導覽條、加 noindex。可重複執行。"""
    for f in ROOT.rglob('*.html'):
        rel = f.relative_to(ROOT)
        if rel.parts[0] in ('.git',):
            continue
        t = f.read_text(encoding='utf-8')
        new = RC.strip_cards(t)
        if rel.parts[0] in ('learn', 'technology', 'skills') and len(rel.parts) > 2:
            new = put_site_strip(new, '../' * (len(rel.parts) - 1), rel.parts[0] + '/')
        new = put_noindex(new)
        if new != t:
            f.write_text(new, encoding='utf-8')


# ---------------------------------------------------------------- 最新消息（每週新文獻）

TOPIC_ORDER = ['羽球', '動作學習', '動作發展', '動作控制']


def news_files() -> list[dict]:
    out = []
    for f in sorted(NEWS_SRC.glob('新文獻_*.json')) if NEWS_SRC.exists() else []:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except ValueError:
            continue
        d['_file'] = f
        out.append(d)
    return out


def build_news(cfg: dict) -> list[str]:
    """每份已整理（reviewed）的新文獻清單 → news/badminton-YYYY-MM-DD/。不公開摘要原文。"""
    notes, issues = [], []
    for d in news_files():
        if not d.get('reviewed'):
            notes.append(f'待整理：{d["_file"].name} 還沒完成篩選與中文重點（reviewed=false），本週不放上網站')
            continue
        items = [x for x in d['items'] if x.get('keep')]
        date = d['date']
        by = {t: [x for x in items if t in x['topics'] and min(TOPIC_ORDER.index(y) for y in x['topics']) == TOPIC_ORDER.index(t)] for t in TOPIC_ORDER}
        secs = ''
        for t in TOPIC_ORDER:
            lst = by[t]
            cards = ''.join(
                f'<article class="card"><small>{esc(x["date"])} · {esc(x["journal"])}{" · 開放取用" if x.get("oa") else ""}'
                f'{" · 也屬" + "、".join(y for y in x["topics"] if y != t) if len(x["topics"]) > 1 else ""}</small>'
                f'<h3 style="margin:.3em 0"><a href="{esc(x["url"])}" target="_blank" rel="noopener">{esc(x["title_zh"] or x["title"])}</a></h3>'
                f'<p>{esc(x["summary_zh"])}</p><p class="muted" style="font-size:14px">原題：{esc(x["title"])}<br>'
                f'{esc("、".join(x["authors"][:3]))}{" 等" if len(x["authors"]) > 3 or x.get("more_authors") else ""}'
                f'{" · 依題名整理" if x.get("basis") == "題名" else " · 依摘要整理，未讀全文"}</p></article>' for x in lst)
            secs += f'<h2 id="{t}">{t}（{len(lst)} 篇）</h2>' + (cards or '<p class="muted">本週沒有符合條件的新論文。</p>')
        counts = '、'.join(f'{t} {len(by[t])}' for t in TOPIC_ORDER)
        body = (f'<p class="crumb"><a href="../">最新消息</a> › {zh_date(date)}</p><h1>本週新文獻：{zh_date(date)}</h1>'
                f'<p class="meta">搜尋期間 {esc(d["range"][0])} 至 {esc(d["range"][1])} · 期刊論文 · 共 {len(items)} 篇（{counts}）</p>'
                f'<div class="card"><p>每星期五晚上搜尋 OpenAlex 與 PubMed 的新發表論文：羽球，以及與運動、技能或兒童相關的動作學習、動作發展、動作控制研究。'
                f'已篩掉工程、臨床醫學等不相關的論文。中文重點只寫摘要提到的研究目的、方法或結果，<mark>沒有讀全文</mark>；按題目會開到原出處。</p>'
                f'<p class="muted">找到 {len(d["items"])} 篇，保留 {len(items)} 篇。</p></div>{secs}')
        out = ROOT / f'news/badminton-{date}'
        out.mkdir(parents=True, exist_ok=True)
        new_html = page(f'本週新文獻 {date}｜最新消息', body, 2, 'news/', f'{date} 羽球與動作學習、發展、控制新論文 {len(items)} 篇。')
        if not (out / 'index.html').exists() or (out / 'index.html').read_text(encoding='utf-8') != new_html:
            if not (out / 'index.html').exists():
                notes.append(f'最新消息新增：本週新文獻 {len(items)} 篇（{counts}）（news/badminton-{date}/）')
            (out / 'index.html').write_text(new_html, encoding='utf-8')
        top = sorted(items, key=lambda x: TOPIC_ORDER.index(min(x['topics'], key=TOPIC_ORDER.index)))
        issues.append({'date': date, 'path': f'news/badminton-{date}/', 'title': f'本週新文獻：{len(items)} 篇',
                       'summary': f'{counts}。', 'top': [{'t': x['title_zh'] or x['title'], 's': x['summary_zh'], 'u': x['url'], 'k': x['topics'][0]} for x in top[:6]]})
    issues.sort(key=lambda i: i['date'], reverse=True)
    cfg['categories']['news']['issues'] = issues
    return notes


# ---------------------------------------------------------------- 每週影片：學生學習與教練科技

WEEKLY_MARK = '<!--weekly-videos-->'


def secs(t: str) -> int:
    n = 0
    for part in t.split(':'):
        n = n * 60 + int(part)
    return n


def fmt_len(sec: int) -> str:
    return f'{sec // 60}:{sec % 60:02d}'


BASIS = {'A': '已讀字幕', 'B': '依影片簡介與章節整理，不是逐字稿', 'C': '只依標題或很短的簡介，細節待看片確認'}


def weekly_target(cat: str, date: str, default_name: str) -> tuple[Path, str]:
    d = ROOT / f'{cat}/badminton-{date}'
    idx = d / 'index.html'
    if idx.exists() and WEEKLY_MARK not in idx.read_text(encoding='utf-8'):
        return d / default_name, f'{cat}/badminton-{date}/{default_name}'   # 同一天已有手寫的一期 → 另開一頁
    return idx, f'{cat}/badminton-{date}/'


def write_audit(folder: Path, date: str, items: list[dict]):
    (folder / '資料').mkdir(parents=True, exist_ok=True)
    vids = [{k: x.get(k) for k in ('id', 'url', 'method', 'checked_date_macau', 'player_status', 'reason', 'has_streams', 'channel',
                                    'duration_seconds', 'publish_date_raw', 'caption_languages', 'access')} | {'original_title': x.get('title')} for x in items]
    data = {'checked_date_macau': date, 'method': 'anonymous YouTube watch-page player response; no account or cookies supplied', 'videos': vids}
    out = folder / f'資料/影片觀看權限核對_{date.replace("-", "")}.json'
    if out.exists():   # 同一天已有手寫一期的核對紀錄 → 合併，保留原有影片，不覆蓋
        try:
            old = json.loads(out.read_text(encoding='utf-8'))
        except ValueError:
            old = {}
        new_ids = {v['id'] for v in vids}
        data = old | {'checked_date_macau': date, 'videos': [v for v in old.get('videos', []) if v.get('id') not in new_ids] + vids}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


LEARN_CSS = '''<style>
.picker{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.picker button{flex:1 1 auto;min-height:44px;padding:8px 14px;border-radius:999px;border:2px solid var(--brand);background:var(--card);color:var(--ink);font:inherit;font-size:15px;cursor:pointer}
.picker button.on{background:var(--brand);color:var(--brand-ink)}
.hint{font-size:17px}.check{font-weight:600;background:var(--code);padding:10px 12px;border-radius:10px}
.tried{display:flex;gap:8px;align-items:center;min-height:44px}.tried input{width:22px;height:22px}
.vid{border:1px dashed var(--line);border-radius:12px;padding:10px 14px;margin:10px 0}
</style>'''
LEARN_JS = '''<script>
(function(){var bs=document.querySelectorAll('.picker button'),ds=document.querySelectorAll('.detail');
bs.forEach(function(b){b.onclick=function(){bs.forEach(function(x){x.classList.toggle('on',x===b)});ds.forEach(function(d){d.hidden=d.dataset.d!==b.dataset.d})}});
document.querySelectorAll('.tried input').forEach(function(c){var k='weekly-'+location.pathname+'-'+c.dataset.k;try{c.checked=localStorage.getItem(k)==='1'}catch(e){}c.onchange=function(){try{localStorage.setItem(k,c.checked?'1':'0')}catch(e){}}});
})();
</script>'''


def learn_page(date: str, items: list[dict]) -> str:
    items = sorted(items, key=lambda x: x['zh'].get('order', 9))
    btns = ''.join(f'<button type="button" data-d="{i}"{" class=on" if i == 0 else ""}>{i + 1} {esc(x["zh"]["title"].split("：")[0])}</button>' for i, x in enumerate(items))
    secs_html = ''
    for i, x in enumerate(items):
        z = x['zh']
        seg = z.get('seg')
        start = secs(seg[0]) if seg else 0
        link = x['url'] + (f'&t={start}s' if start else '')
        seg_txt = (f'{esc(seg[0])} 起（{esc(seg[2])}）' if seg else f'全片 {fmt_len(x["duration_seconds"])}（影片沒有章節，從頭看）')
        look = ''.join(f'<li>{esc(t)}</li>' for t in z['look'])
        steps = ''.join(f'<li>{esc(t)}</li>' for t in z['steps'])
        warn = f'<p class="check" style="background:#fde8e8;color:#7a1d1d">⚠️ {esc(z["warn"])}</p>' if z.get('warn') else ''
        secs_html += f'''<section class="detail card" data-d="{i}"{" hidden" if i else ""}>
<h3>細節 {i + 1}｜{esc(z["title"])}</h3>
<p class="hint">💡 一句提示：<mark>{esc(z["hint"])}</mark></p>
<p class="muted">{esc(z["facts"])}</p>
<p><b>看甚麼</b></p><ul>{look}</ul>
<p><b>怎樣練</b> <small class="muted">（{esc(z["steps_src"])}）</small></p><ol>{steps}</ol>
<p class="check">✅ 只記一項：{esc(z["record"])}</p>{warn}
<div class="vid"><p><b>看影片</b>：<a href="{esc(link)}" target="_blank" rel="noopener">{esc(x["title"])}</a></p>
<p class="muted" style="font-size:14px">{esc(x["channel"])} · {esc((x.get("publish_date_raw") or "")[:10])} 發佈 · 片長 {fmt_len(x["duration_seconds"])} · 先看：{seg_txt}<br>
原音：{esc(z["lang"])} · {esc(BASIS[z["basis"]])} · {esc(x["checked_date_macau"])} 以未登入狀態核對可免費觀看；影片簡介中的課程或商品不用購買</p></div>
<label class="tried"><input type="checkbox" data-k="{esc(x["id"])}"> 我這週試過這個細節</label>
</section>'''
    return f'''{LEARN_CSS}<p class="crumb"><a href="../">學生學習</a> › {zh_date(date)}</p>
<h1>本週影片精華：{len(items)} 個細節</h1>
<p class="meta">{zh_date(date)} · 影片都是本週新發佈、已核對免費觀看 · 每次只練一個細節</p>
<div class="card"><p>按下面的數字按鈕換細節。每個細節都有：一句提示 → 看甚麼 → 怎樣練 → 只記一項結果。影片只看標示的那一段就可以。</p>
<p class="muted">練法來源寫在「怎樣練」旁邊；「本頁編製」代表影片沒有列出練法，是本頁依影片重點設計的。</p></div>
<div class="picker">{btns}</div>{secs_html}
<p class="muted" style="font-size:14px">「我這週試過」只存在這部裝置的瀏覽器，不會上傳；勾了只代表試過，不代表學會。</p>{LEARN_JS}'''


def tech_page(date: str, items: list[dict]) -> str:
    items = sorted(items, key=lambda x: x['zh'].get('order', 9))
    rows = ''.join(f'<tr><td>{i + 1}</td><td>{esc(x["zh"]["title"])}</td><td>{esc(x["zh"]["basis"])}</td><td>{esc(x["zh"]["lang"])}</td></tr>' for i, x in enumerate(items))
    cards = ''
    for i, x in enumerate(items):
        z = x['zh']
        cards += f'''<article class="card"><small>T{i + 1} · {esc(x["channel"])} · {esc((x.get("publish_date_raw") or "")[:10])} · 片長 {fmt_len(x["duration_seconds"])} · 依據 {esc(z["basis"])}</small>
<h3 style="margin:.3em 0"><a href="{esc(x["url"])}" target="_blank" rel="noopener">{esc(z["title"])}</a></h3>
<p>💡 <mark>{esc(z["point"])}</mark></p>
<table><thead><tr><th>項目</th><th>內容</th></tr></thead><tbody>
<tr><td>訓練用途</td><td>{esc(z["use"])}</td></tr><tr><td>使用條件與成本</td><td>{esc(z["cond"])}</td></tr>
<tr><td>原音／字幕</td><td>{esc(z["lang"])}</td></tr><tr><td>依據</td><td>{esc(BASIS[z["basis"]])}</td></tr></tbody></table>
<p class="muted" style="font-size:14px">原標題：{esc(x["title"])} · {esc(x["checked_date_macau"])} 以未登入狀態核對可免費觀看（影片免費不代表產品免費）</p></article>'''
    return f'''<p class="crumb"><a href="../">教練科技</a> › {zh_date(date)}</p>
<h1>本週羽球科技：{len(items)} 支新影片</h1>
<p class="meta">{zh_date(date)} · 給教練 · 本週新發佈、已核對免費觀看</p>
<div class="card"><p>本週新的發球機、感測器、AI 分析類影片不多；以下是與器材和訓練工具有關、內容足以整理的影片。依據標記：<b>A</b> 已讀字幕、<b>B</b> 依簡介與章節、<b>C</b> 只依標題。</p>
<p class="muted">器材效果、價格與行銷說法都<mark>未驗證</mark>，採購前請小規模試用。</p></div>
<table><thead><tr><th>編號</th><th>主題</th><th>依據</th><th>原音</th></tr></thead><tbody>{rows}</tbody></table>{cards}'''


def build_weekly_videos(cfg: dict) -> list[str]:
    notes = []
    files = sorted(VIDEO_SRC.glob('影片候選_*.json')) if VIDEO_SRC.exists() else []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except ValueError:
            continue
        if not d.get('reviewed'):
            notes.append(f'待整理：{f.name} 還沒完成篩選（reviewed=false），本週影片不放上網站')
            continue
        date = d['date']
        for cat, name, maker, title_fmt, summ_fmt in (
                ('learn', '本週影片精華.html', learn_page, '本週影片精華：{n} 個細節', '本週新發佈、已核對免費觀看的教學影片，每支練一個細節：{t}。'),
                ('technology', '本週科技.html', tech_page, '本週羽球科技：{n} 支新影片', '{t}。')):
            items = [x for x in d['items'] if x.get('keep') and x.get('section') == ('learn' if cat == 'learn' else 'tech')
                     and x.get('access') == 'free_public']
            if not items:
                notes.append(f'{"學生學習" if cat == "learn" else "教練科技"} {date}：本週沒有合適的免費新影片，不出新一期')
                continue
            target, path = weekly_target(cat, date, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            up = 2
            html_ = page(title_fmt.format(n=len(items)) + ('｜學生學習' if cat == 'learn' else '｜教練科技'),
                         WEEKLY_MARK + maker(date, items), up, f'{cat}/', summ_fmt.format(n=len(items), t='、'.join(x['zh']['title'].split('：')[0] for x in sorted(items, key=lambda x: x['zh'].get('order', 9)))))
            old = target.read_text(encoding='utf-8') if target.exists() else None
            if old != html_:
                target.write_text(html_, encoding='utf-8')
                if old is None:
                    notes.append(f'{"學生學習" if cat == "learn" else "教練科技"}新增一期：{title_fmt.format(n=len(items))}（{path}）')
            write_audit(target.parent, date, items)
            issue = {'date': date, 'path': path, 'title': title_fmt.format(n=len(items)),
                     'summary': summ_fmt.format(n=len(items), t='、'.join(x['zh']['title'].split('：')[0] for x in sorted(items, key=lambda x: x['zh'].get('order', 9)))), 'auto': True}
            lst = [i for i in cfg['categories'][cat]['issues'] if i.get('path') != path]
            lst.append(issue)
            lst.sort(key=lambda i: (i['date'], bool(i.get('auto'))), reverse=True)
            cfg['categories'][cat]['issues'] = lst
    return notes


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
    news = cats.get('news', {}).get('issues', [])
    cards = ''
    for key in order:
        c = cats[key]
        it = c['issues'][0]
        cards += (f'<article class="card cat" style="--h:{CAT_HUE.get(key, 160)}"><span class="tag">{esc(c["audience"])}</span><small>最新 {it["date"]}</small>'
                  f'<h2 style="margin-top:.4em">{esc(c["name"])}</h2><p>{esc(c["intro"])}</p>'
                  f'<p><b>{esc(it["title"])}</b><br><small>{esc(it["summary"])}</small></p>'
                  f'<p class="big"><a href="{it["path"]}">打開最新一期</a></p><p><a href="{key}/">看全部 {len(c["issues"])} 期 →</a></p></article>')
    last = log[0] if log else {'date': today(), 'items': []}
    if news:
        n0 = news[0]
        lis = ''.join(f'<li><span class="tag">{esc(x["k"])}</span><a href="{esc(x["u"])}" target="_blank" rel="noopener">{esc(x["t"])}</a><br><small>{esc(x["s"])}</small></li>' for x in n0['top'])
        news_block = (f'<section class="card cat" style="--h:{CAT_HUE["news"]}"><small>最新消息 · 每星期五晚上搜尋、星期六早上更新</small>'
                      f'<h2 style="margin-top:.3em">{esc(n0["title"])}（{zh_date(n0["date"])}）</h2><p class="muted">{esc(n0["summary"])}</p>'
                      f'<ul style="padding-left:0;list-style:none;display:grid;gap:10px">{lis}</ul>'
                      f'<p class="big"><a href="{n0["path"]}">看本週全部新文獻</a></p><p><a href="news/">往期最新消息 →</a> · <a href="updates/">網站更新紀錄 →</a></p></section>')
    else:
        news_block = ''
    upd = ''.join(f'<li>{esc(x)}</li>' for x in last['items'][:4]) or '<li>本週本機資料沒有變動。</li>'
    body = f"""<section class="hero" data-court="rally"><div class="hero-text"><h1>小選手，大目標。</h1>
<p>羽球學習與教練資料站：學生從細節開始練，教練用研究和科技安排訓練。</p>
<p class="hero-tip">旁邊的 3D 羽球場會自動對打；點一下球場，就會朝那裡殺球。</p></div></section>
{news_block}
<div class="grid home">{cards}</div>
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
    items += build_news(cfg)
    items += build_weekly_videos(cfg)
    tidy_hand_pages()
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
