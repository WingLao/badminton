#!/usr/bin/env python3
"""產生教練科技「GitHub 羽球開源工具圖鑑」頁。

用法（在儲存庫根目錄）：python3 tools/github_catalog.py
讀：technology/badminton-2026-11-27/資料/工具資料_20261127.json
寫：technology/badminton-2026-11-27/index.html
資料改了（星數、授權、更正）就重跑一次，再跑 build_site.py 和 check_site.py。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site import page, esc, zh_date  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'technology/badminton-2026-11-27'
DATA = FOLDER / '資料/工具資料_20261127.json'
BASIS = {'A': 'A：已讀 README 原文', 'B': 'B：README 簡短，部分依官方簡介與影片說明', 'C': 'C：只有標題'}

CSS = """<style>
.gc-tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:16px 0}
.gc-pill{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:8px 14px;font:inherit;font-size:15px;cursor:pointer;min-height:40px}
.gc-pill[aria-pressed="true"]{background:var(--brand);color:var(--brand-ink);border-color:var(--brand);font-weight:700}
.gc-search{flex:1 1 220px;min-width:0;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;padding:9px 12px;font:inherit;font-size:16px}
.gc-grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(min(340px,100%),1fr))}
.gc-card{background:var(--card);border:1px solid var(--line);border-top:5px solid hsl(215 55% 42%);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.gc-stage{position:relative;aspect-ratio:16/9;background:#020617}
.gc-stage img,.gc-stage canvas{display:block;width:100%;height:100%;object-fit:cover;border-radius:0}
.gc-stage .gc-len{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.75);color:#fff;font-size:13px;padding:1px 7px;border-radius:6px}
.gc-stage .gc-play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:58px;height:40px;border-radius:12px;background:rgba(220,38,38,.92)}
.gc-stage .gc-play::after{content:"";position:absolute;left:23px;top:11px;border-style:solid;border-width:9px 0 9px 15px;border-color:transparent transparent transparent #fff}
.gc-stage .gc-simtag{position:absolute;left:8px;top:8px;background:rgba(0,0,0,.65);color:#fde047;font-size:12px;padding:1px 8px;border-radius:6px}
.gc-stage [hidden]{display:none}
.gc-switch{display:flex;gap:6px;padding:8px;border-bottom:1px solid var(--line)}
.gc-switch button{flex:1;border:1px solid transparent;background:transparent;color:var(--muted);border-radius:8px;padding:7px 6px;font:inherit;font-size:14px;cursor:pointer}
.gc-switch button[aria-pressed="true"]{background:var(--code);color:var(--ink);border-color:var(--line);font-weight:700}
.gc-body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}
.gc-body h3{margin:0;font-size:19px}
.gc-repo{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:var(--muted)}
.gc-body p{margin:0}
.gc-dl{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:15px;margin:0}
.gc-dl dt{color:var(--muted);font-weight:600;white-space:nowrap}
.gc-dl dd{margin:0}
.gc-cmd{margin-top:auto;display:flex;gap:8px;align-items:center;background:var(--code);border-radius:10px;padding:8px 10px}
.gc-cmd code{flex:1;min-width:0;overflow-x:auto;white-space:nowrap;background:none;padding:0;font-size:13px}
.gc-cmd button{flex-shrink:0;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 10px;font:inherit;font-size:14px;cursor:pointer}
.gc-empty{display:none;color:var(--muted)}
.gc-card[hidden]{display:none}
.gc-chip{display:inline-block;font-size:13px;padding:1px 9px;border-radius:999px;background:hsl(215 55% 42% / .12);color:var(--blue);margin-right:4px}
</style>"""

JS = r"""<script>
(function(){
var cat='全部',q='',cards=[].slice.call(document.querySelectorAll('.gc-card')),empty=document.querySelector('.gc-empty');
function apply(){var n=0;cards.forEach(function(c){var ok=(cat==='全部'||c.dataset.cat===cat)&&(!q||c.dataset.text.indexOf(q)>-1);c.hidden=!ok;if(ok)n++});empty.style.display=n?'none':'block'}
document.querySelectorAll('.gc-pill').forEach(function(b){b.onclick=function(){cat=b.dataset.cat;document.querySelectorAll('.gc-pill').forEach(function(x){x.setAttribute('aria-pressed',x===b)});apply()}});
document.querySelector('.gc-search').oninput=function(e){q=e.target.value.trim().toLowerCase();apply()};
document.querySelectorAll('.gc-switch button').forEach(function(b){b.onclick=function(){var card=b.closest('.gc-card');
 card.querySelectorAll('.gc-switch button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});
 card.querySelectorAll('[data-pane]').forEach(function(p){p.hidden=p.dataset.pane!==b.dataset.show})}});
document.querySelectorAll('.gc-cmd button').forEach(function(b){b.onclick=function(){var t=b.previousElementSibling.textContent;
 (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent='已複製 ✓'},function(){b.textContent='請手動選取'});setTimeout(function(){b.textContent='複製'},1500)}});
var data=JSON.parse(document.getElementById('gc-data').textContent);
document.getElementById('gc-export').onclick=function(){var L=['# GitHub 羽球開源工具圖鑑（查核：'+data.checked_date_macau+'）','','| 分類 | 工具 | 用途 | 授權 | GitHub |','| --- | --- | --- | --- | --- |'];
 data.tools.forEach(function(t){L.push('| '+t.category+' | '+t.name+' | '+t.use+' | '+t.license+' | https://github.com/'+t.repo+' |')});
 data.tools.forEach(function(t){L.push('','## '+t.name,'- 說明：'+t.desc,'- 數據：'+t.metric,'- 使用條件與成本：'+t.cond,'- 快速開始：`'+t.cmd+'`')});
 var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([L.join('\n')],{type:'text/markdown;charset=utf-8'}));a.download='羽球開源工具圖鑑.md';a.click()};
// 示意動畫：只在看得到時畫；系統「減少動態效果」時只畫一格
var still=matchMedia('(prefers-reduced-motion: reduce)').matches,vis=new Set();
var io='IntersectionObserver' in window?new IntersectionObserver(function(es){es.forEach(function(e){e.isIntersecting?vis.add(e.target):vis.delete(e.target)})}):null;
var cvs=[].slice.call(document.querySelectorAll('canvas[data-sim]'));cvs.forEach(function(c){io?io.observe(c):vis.add(c)});
function court(x,w,h){x.fillStyle='#064e3b';x.fillRect(40,30,w-80,h-60);x.strokeStyle='rgba(255,255,255,.4)';x.lineWidth=2;x.strokeRect(40,30,w-80,h-60);
 x.beginPath();x.moveTo(w/2,30);x.lineTo(w/2,h-30);x.moveTo(40,52);x.lineTo(w-40,52);x.moveTo(40,h-52);x.lineTo(w-40,h-52);x.stroke()}
function label(x,s){x.fillStyle='#e2e8f0';x.font='bold 16px sans-serif';x.fillText(s,48,22)}
function draw(c,t){if(c.offsetParent===null)return;var x=c.getContext('2d'),w=c.width,h=c.height,k=c.dataset.sim;x.fillStyle='#020617';x.fillRect(0,0,w,h);
 if(k==='trajectory'||k==='rallylens'){court(x,w,h);for(var i=0;i<24;i++){var p=((t*.8-i*.025)%1+1)%1;x.beginPath();x.arc(90+p*(w-180),h/2-Math.sin(p*Math.PI)*110,i?4:7,0,7);x.fillStyle=i?'rgba(56,189,248,'+(1-i/24)*.85+')':'#fde047';x.fill()}
  if(k==='rallylens'){[[115,h/2+Math.sin(t*2.2)*55,'#38bdf8'],[w-115,h/2-Math.cos(t*1.9)*55,'#f472b6']].forEach(function(a){x.strokeStyle=a[2];x.lineWidth=2.5;x.strokeRect(a[0]-22,a[1]-34,44,68)});
   x.fillStyle='rgba(15,23,42,.85)';x.fillRect(w-150,h-110,110,80);x.strokeStyle='#94a3b8';x.strokeRect(w-150,h-110,110,80)}
  label(x,k==='trajectory'?'逐格找出球的位置（黃點），連成球路':'骨架框＋球路尾跡＋右下俯視小地圖')}
 else if(k==='heatmap'){court(x,w,h);[[170,140,45],[210,220,55],[460,180,60],[500,120,40]].forEach(function(s,i){var r=s[2]+Math.sin(t*3+i)*8,g=x.createRadialGradient(s[0],s[1],4,s[0],s[1],r);
  g.addColorStop(0,'rgba(239,68,68,.85)');g.addColorStop(.5,'rgba(245,158,11,.45)');g.addColorStop(1,'rgba(245,158,11,0)');x.fillStyle=g;x.beginPath();x.arc(s[0],s[1],r,0,7);x.fill()});label(x,'俯視球場上的站位熱區')}
 else if(k==='tactics'){court(x,w,h);var n=[[140,110],[180,240],[490,100],[470,250],[320,180]],a=Math.floor(t*1.5)%n.length;x.strokeStyle='rgba(56,189,248,.7)';x.lineWidth=2;
  for(var j=0;j<n.length-1;j++){x.beginPath();x.moveTo(n[j][0],n[j][1]);x.lineTo(n[j+1][0],n[j+1][1]);x.stroke()}
  n.forEach(function(p,i){x.beginPath();x.arc(p[0],p[1],i===a?12:7,0,7);x.fillStyle=i===a?'#10b981':'#38bdf8';x.fill()});label(x,'逐拍落點序列 → 預測下一拍')}
 else if(k==='autoclip'){x.fillStyle='#0f172a';x.fillRect(30,70,w-60,110);[[0,.14,0],[.14,.34,1],[.34,.48,0],[.48,.72,1],[.72,.82,0],[.82,.98,1]].forEach(function(s){x.fillStyle=s[2]?'#10b981':'#334155';x.fillRect(40+s[0]*(w-80),95,(s[1]-s[0])*(w-80)-4,60)});
  var sx=40+((t*.25)%1)*(w-80);x.strokeStyle='#fde047';x.lineWidth=3;x.beginPath();x.moveTo(sx,75);x.lineTo(sx,175);x.stroke();x.fillStyle='#10b981';x.font='bold 18px sans-serif';x.fillText('綠色＝保留回合　灰色＝剪走撿球、休息',50,235);label(x,'自動找回合、剪掉空檔')}
 else if(k==='stringer'){x.strokeStyle='#334155';x.lineWidth=2;x.strokeRect(50,60,w-100,220);x.strokeStyle='#38bdf8';x.lineWidth=3;x.beginPath();
  for(var X=0;X<w-120;X+=6){var y=260-Math.min(1,X/(w-120)*3.2)*145+Math.sin(t*5+X*.05)*2.5;X?x.lineTo(60+X,y):x.moveTo(60+X,y)}x.stroke();x.fillStyle='#10b981';x.font='bold 22px sans-serif';x.fillText('拉到設定磅數後保持恆定',65,105);label(x,'恆拉：荷重元讀數 → 馬達微調')}
 else if(k==='feeder'){court(x,w,h);x.fillStyle='#f59e0b';x.fillRect(60,h/2-18,36,36);for(var m=0;m<3;m++){var q2=(t*.9+m*.33)%1;x.beginPath();x.arc(96+q2*(w-170),h/2-Math.sin(q2*Math.PI)*(60+m*35),6,0,7);x.fillStyle='#fde047';x.fill()}label(x,'馬達控制角度與力度，把球送出')}
 else if(k==='tournament'){for(var r=0;r<3;r++){var Y=65+r*85;x.fillStyle='#1e293b';x.fillRect(45,Y,w-90,68);x.strokeStyle=r===Math.floor(t)%3?'#38bdf8':'#334155';x.lineWidth=2;x.strokeRect(45,Y,w-90,68);
  x.fillStyle='#38bdf8';x.font='bold 16px sans-serif';x.fillText((r+1)+' 號場',65,Y+40);x.fillStyle='#f1f5f9';x.fillText('選手 A　對　選手 B',170,Y+40)}label(x,'場地分配與賽程看板')}}
function loop(ts){cvs.forEach(function(c){if(vis.has(c))draw(c,ts/1000)});if(!still&&!document.hidden)requestAnimationFrame(loop)}
document.addEventListener('visibilitychange',function(){if(!document.hidden&&!still)requestAnimationFrame(loop)});
if(still){cvs.forEach(function(c){draw(c,1.2)});document.querySelectorAll('.gc-switch button').forEach(function(b){b.addEventListener('click',function(){setTimeout(function(){cvs.forEach(function(c){draw(c,1.2)})},0)})})}
else requestAnimationFrame(loop);
})();
</script>"""


def card(t: dict) -> str:
    url = f'https://github.com/{t["repo"]}'
    if t.get('video'):
        v = t['video']
        media = (f'<a href="https://www.youtube.com/watch?v={v["id"]}" target="_blank" rel="noopener" aria-label="在 YouTube 看 {esc(t["name"])} 示範影片">'
                 f'<img src="圖片/{v["id"]}.jpg" alt="{esc(t["name"])} 示範影片縮圖" loading="lazy"><span class="gc-play"></span><span class="gc-len">{v["len"]}</span></a>')
        tab1 = '▶ 示範影片'
        vnote = f'<p class="muted" style="font-size:14px">影片：{esc(v["note"])} · 2026-11-27 未登入核對可免費觀看</p>'
    else:
        media = f'<a href="{url}" target="_blank" rel="noopener"><img src="圖片/{t["img"]}" alt="{esc(t["name"])} GitHub 預覽圖" loading="lazy"></a>'
        tab1 = '🖼 GitHub 預覽'
        vnote = '<p class="muted" style="font-size:14px">沒有找到作者的示範影片。</p>'
    text = ' '.join([t['name'], t['repo'], t['category'], t['desc'], t['use'], t['cond'], *t['tech']]).lower()
    return f'''<article class="gc-card" data-cat="{esc(t["category"])}" data-text="{esc(text)}">
<div class="gc-stage"><div data-pane="media">{media}</div><div data-pane="sim" hidden><canvas data-sim="{t["sim"]}" width="640" height="360" aria-label="功能示意動畫"></canvas><span class="gc-simtag">示意動畫，不是真實數據</span></div></div>
<div class="gc-switch"><button type="button" data-show="media" aria-pressed="true">{tab1}</button><button type="button" data-show="sim" aria-pressed="false">✨ 功能示意</button></div>
<div class="gc-body"><p><span class="gc-chip">{esc(t["category"])}</span><span class="tag">依據 {t["basis"]}</span></p>
<h3><a href="{url}" target="_blank" rel="noopener">{esc(t["name"])} ↗</a></h3><div class="gc-repo">{esc(t["repo"])} · ★ {t["stars"]} · 最後更新 {t["pushed"]}</div>
<p>{esc(t["desc"])}</p>
<dl class="gc-dl"><dt>訓練用途</dt><dd>{esc(t["use"])}</dd><dt>公開數據</dt><dd>{esc(t["metric"])}</dd><dt>條件與成本</dt><dd>{esc(t["cond"])}</dd><dt>授權</dt><dd>{esc(t["license"])}</dd></dl>
{vnote}
<div class="gc-cmd"><code>{esc(t["cmd"])}</code><button type="button">複製</button></div></div></article>'''


def main():
    d = json.loads(DATA.read_text(encoding='utf-8'))
    tools = d['tools']
    cats = ['全部'] + list(dict.fromkeys(t['category'] for t in tools))
    pills = ''.join(f'<button type="button" class="gc-pill" data-cat="{esc(c)}" aria-pressed="{str(c == "全部").lower()}">{esc(c)}</button>' for c in cats)
    rows = ''.join(f'<tr><td>{esc(t["name"])}</td><td>{esc(t["category"])}</td><td>{esc(t["use"])}</td><td>{esc(t["license"])}</td><td>★ {t["stars"]} · {t["pushed"]}</td><td>{t["basis"]}</td></tr>' for t in tools)
    fixes = ''.join(f'<li>{esc(x)}</li>' for x in d['corrections'])
    video_n = sum(1 for t in tools if t.get('video'))
    body = f'''{CSS}<p class="crumb"><a href="../">教練科技</a> › {zh_date(d["checked_date_macau"])}</p>
<h1>GitHub 羽球開源工具圖鑑</h1>
<p class="meta">{zh_date(d["checked_date_macau"])} · 給教練 · {len(tools)} 個開源專案 · {video_n} 支示範影片已核對免費觀看</p>
<div class="card"><h2 style="margin-top:0">一分鐘重點</h2><ul>
<li><mark>影像追蹤最成熟</mark>：TrackNetV3 找球、RallyLens 一條指令出骨架＋球路＋跑動距離，但都要會 Python、最好有顯示卡。</li>
<li><mark>想直接用、不寫程式</mark>：只有「弧迹」有安裝版（Android／Windows／Linux），自動剪掉撿球片段。</li>
<li><mark>戰術研究</mark>：CoachAI 的 ShuttleSet 是專業比賽逐拍資料，適合研究或帶數據專題，不是自己球隊的數據。</li>
<li><mark>器材 DIY</mark>：PicoBETH 自製電子拉線頭、BADDY 羽球機器人；都要動手組裝，BADDY 已多年沒更新。</li>
<li>所有準確率都是<mark>作者自己的測試</mark>，換成你的場館燈光、拍攝角度要重新試。</li></ul></div>
<p class="muted">看不懂的英文名詞（例如 README、授權、骨架偵測），見文末<a href="#gc-words">名詞小字典</a>。</p>
<h2>比較表</h2>
<table><thead><tr><th>工具</th><th>分類</th><th>訓練用途</th><th>授權</th><th>活躍度</th><th>依據</th></tr></thead><tbody>{rows}</tbody></table>
<h2>逐個看</h2>
<p>按分類或輸入關鍵字篩選。每張卡上方可切換「示範影片／GitHub 預覽」與「功能示意」動畫；示意動畫只說明工具在做甚麼，<b>不是真實數據</b>。</p>
<div class="gc-tools">{pills}<input class="gc-search" type="search" placeholder="搜尋工具、功能或技術，例如：骨架" aria-label="搜尋工具"></div>
<p class="gc-empty">找不到符合的工具，請換一個關鍵字或按「全部」。</p>
<div class="gc-grid">{"".join(card(t) for t in tools)}</div>
<h2>使用前注意</h2>
<ul><li>開源免費指軟件本身；顯示卡、雲端服務（例如 RallyLens 的 Gemini 報告）和硬件零件可能要付費，金額<mark>未驗證</mark>。</li>
<li>拍攝學生影片前先取得同意；上傳到雲端分析的工具（弧迹雲端模式、RallyLens 報告）要特別注意私隱。</li>
<li>授權寫「AGPL-3.0」或「非商業」的專案，改了再對外提供或銷售前，要先讀授權條款。</li>
<li>建議先拿一段 1 分鐘的練習影片小規模試，確認在自己場館的準確度，再放進正式訓練流程。</li></ul>
<h2 id="gc-words">名詞小字典</h2>
<table><thead><tr><th>名詞</th><th>意思</th></tr></thead><tbody>
<tr><td>GitHub</td><td>放程式碼的網站；每個工具是一個「儲存庫」（repository，簡稱 repo），網址是 github.com/作者/名稱。</td></tr>
<tr><td>README</td><td>儲存庫首頁的說明檔，寫功能、安裝方法和測試結果；本頁的數字都從這裡核對。</td></tr>
<tr><td>★ 星數</td><td>GitHub 使用者按「收藏」的次數，可粗略看出多少人關注，不代表品質。</td></tr>
<tr><td>授權（License）</td><td>規定可否修改、轉售；MIT 最寬鬆，AGPL-3.0 改了再公開提供要公開原始碼，「非商業」不可拿去賣。</td></tr>
<tr><td>git clone</td><td>把整個儲存庫下載到自己電腦的指令；卡片底部「複製」按鈕複製的就是這行。</td></tr>
<tr><td>Python／PyTorch</td><td>程式語言／深度學習工具；影像分析工具大多要用到。</td></tr>
<tr><td>顯示卡（GPU）</td><td>電腦的繪圖晶片，AI 影像分析用它會快很多，NVIDIA 最常用。</td></tr>
<tr><td>骨架偵測（Pose）</td><td>AI 在畫面中找出肩、肘、膝等關節點，連成火柴人，用來分析動作與站位。</td></tr>
<tr><td>透視校正（Homography）</td><td>把斜角拍攝的球場換算成從正上方看的平面座標，才可以畫小球場和算跑動距離。</td></tr>
<tr><td>示意動畫</td><td>本頁自己畫的動畫，只說明工具在做甚麼，不是工具真正輸出的數據。</td></tr>
</tbody></table>
<h2>資料依據</h2>
<p>查核日期 {d["checked_date_macau"]}（澳門時間）：星數、授權、最後更新日期由 GitHub API 讀取；功能、數字與安裝指令逐項對照各專案 README；示範影片以未登入狀態核對可免費播放。
依據標記：<b>A</b> 已讀 README 原文、<b>B</b> README 簡短，部分依官方簡介與影片說明。星數會變動，以 GitHub 頁面為準。</p>
<details><summary>與原圖鑑相比的更正（{len(d["corrections"])} 項）</summary><ul>{fixes}</ul></details>
<p class="big"><a href="#" id="gc-export" role="button">⬇ 下載 Markdown 筆記</a></p>
<script type="application/json" id="gc-data">{json.dumps({"checked_date_macau": d["checked_date_macau"], "tools": tools}, ensure_ascii=False).replace("</", "<\\/")}</script>
{JS}'''
    html_ = page('GitHub 羽球開源工具圖鑑｜教練科技', body, 2, 'technology/',
                 f'{len(tools)} 個羽球開源專案：影像追蹤、動作與戰術、影片剪輯、器材 DIY、賽事管理的用途、條件與成本。')
    (FOLDER / 'index.html').write_text(html_, encoding='utf-8')
    print(f'已產生 {FOLDER.relative_to(ROOT)}/index.html：{len(tools)} 個工具')


if __name__ == '__main__':
    main()
