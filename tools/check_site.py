#!/usr/bin/env python3
"""Check published file links, exact URL case, and audited YouTube access.
Uses the saved playback audit; does not perform a new YouTube access check.
"""
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs
import html
import json
import posixpath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts}
audit_path = ROOT / 'learn/badminton-2026-11-15/資料/影片觀看權限核對_20261115.json'
audit = json.loads(audit_path.read_text(encoding='utf-8'))
videos = {v['id']: v for v in audit['videos']}
# 每週影片頁各有自己的核對紀錄（資料/影片觀看權限核對_YYYYMMDD.json）
for extra in sorted(ROOT.glob('*/badminton-*/資料/影片觀看權限核對_*.json')):
    if extra == audit_path:
        continue
    for v in json.loads(extra.read_text(encoding='utf-8')).get('videos', []):
        videos.setdefault(v['id'], v)
errors = []
checked = 0
public_videos = set()
for name in sorted(files):
    path = ROOT / name
    if path.suffix not in {'.html', '.md'}:
        continue
    source = path.read_text(encoding='utf-8')
    links = re.findall(r'(?:href|src)="([^"]+)"', source) if path.suffix == '.html' else re.findall(r'\]\(([^)]+)\)', source)
    for target in links:
        checked += 1
        parsed = urlsplit(html.unescape(target))
        if parsed.netloc in {'www.youtube.com', 'youtube.com', 'youtu.be'}:
            video_id = parse_qs(parsed.query).get('v', [parsed.path.lstrip('/') if parsed.netloc == 'youtu.be' else ''])[0]
            if videos.get(video_id, {}).get('access') != 'free_public':
                errors.append(f'{name}: YouTube 來源未核實為免費：{video_id}')
            public_videos.add(video_id)
            continue
        if parsed.scheme or parsed.netloc:
            if parsed.netloc != 'winglao.github.io' or not parsed.path.startswith('/badminton/'):
                continue
            candidate = unquote(parsed.path[len('/badminton/'):])
        elif parsed.path:
            candidate = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
        else:
            continue
        candidate = candidate.lstrip('/')
        if candidate in {'', '.'}:
            candidate = 'index.html'
        if candidate not in files:
            candidate = candidate.rstrip('/') + '/index.html'
        if candidate not in files:
            errors.append(f'{name}: 檔案不存在或網址大小寫不符：{target}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    raise SystemExit(1)
print(f'檢查通過：{checked} 個連結，{len(public_videos)} 支公開推薦影片均符合既有免費核對紀錄。')
print('這是檔案／大小寫與既有紀錄檢查，不是即時重新驗證影片權限或器材效果。')
