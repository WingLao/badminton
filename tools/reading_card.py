"""閱讀卡元件：把使用者〈閱讀與記憶工作流〉套用到每篇文章。

一張閱讀卡 = 我讀這篇要回答甚麼 → 選讀法（查資料／做決定／日後要教）→ 四欄筆記 → 閉卷回想 → 隔天與第 7 天複習。
樣式與程式都包在區塊內（class 以 rc- 開頭），可以放進任何頁面，包括舊版設計的頁面。
"""
from __future__ import annotations

import html
import json
import re

START, END = '<!--rc:start-->', '<!--rc:end-->'
SITE_START, SITE_END = '<!--site:start-->', '<!--site:end-->'


def esc(s) -> str:
    return html.escape(str(s or ''))


MODES = [
    ('lookup', '查資料', '先讀哪裡：用頁內搜尋（電腦按 Ctrl＋F 或 ⌘＋F；手機在瀏覽器選單選「在頁面中尋找」）找關鍵詞{kw}，直接讀範例和適用條件。',
     '何時停：找到答案，並能在手上的例子用一次。'),
    ('decide', '做決定', '先讀哪裡：先看下面的四欄筆記和本頁圖表，再核對比較對象、指標和適用條件。',
     '何時停：能說出要改哪一步、觀察甚麼，以及哪項證據可能改變決定。'),
    ('teach', '日後要教或反覆用', '先讀哪裡：一次讀一節，關掉原文，用約 1 分鐘畫出三格流程，再回原文核對（可對照下面的「因果／流程」）。',
     '何時停：能換一個情境說明，並指出一個適用條件或常見錯誤。'),
]

CSS = r"""<style>
.rc{--rc-card:var(--card,#fff);--rc-ink:var(--ink,#16302a);--rc-muted:var(--muted,#5d726b);--rc-line:var(--line,#d8e2dd);--rc-soft:var(--code,#eef3f0);--rc-acc:#d7f24b;--rc-brand:var(--brand,#0f5a46);
 font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang TC","Noto Sans TC",sans-serif;color:var(--rc-ink);background:var(--rc-card);border:1px solid var(--rc-line);border-radius:18px;padding:18px 18px 8px;margin:18px 0 22px;text-align:left;box-sizing:border-box;max-width:100%}
.rc *{box-sizing:border-box}
.rc-head{display:flex;gap:8px;align-items:center;font-size:13px;font-weight:700;letter-spacing:.04em;color:var(--rc-muted);text-transform:none}
.rc-head b{background:var(--rc-acc);color:#16302a;border-radius:999px;padding:2px 10px}
.rc-q{font-size:18px;font-weight:700;line-height:1.5;margin:8px 0 12px}
.rc-q small{display:block;font-size:13px;font-weight:400;color:var(--rc-muted)}
.rc-modes{display:flex;flex-wrap:wrap;gap:8px}
.rc-modes button{flex:1 1 auto;min-height:44px;border:2px solid var(--rc-line);background:transparent;color:var(--rc-ink);border-radius:999px;padding:6px 14px;font:inherit;font-size:15px;cursor:pointer}
.rc-modes button[aria-pressed="true"]{border-color:var(--rc-ink);background:var(--rc-ink);color:var(--rc-card)}
.rc-tip{background:var(--rc-soft);border-radius:12px;padding:10px 14px;margin:10px 0 4px;font-size:15px}
.rc-tip p{margin:4px 0}
.rc-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0}
@media (max-width:640px){.rc-grid{grid-template-columns:1fr}}
.rc-cell{border:1px solid var(--rc-line);border-radius:14px;padding:10px 14px}
.rc-cell h4{margin:0 0 4px;font-size:14px;color:var(--rc-muted);font-weight:700}
.rc-cell h4 span{font-weight:400;font-size:12px;margin-left:4px}
.rc-cell p,.rc-cell ul{margin:4px 0;font-size:15px}
.rc-cell ul{padding-left:18px}
.rc-cell li small{color:var(--rc-muted)}
.rc-flow{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:14px}
.rc-flow span{background:var(--rc-soft);border-radius:8px;padding:4px 8px}
.rc-flow i{font-style:normal;color:var(--rc-muted)}
.rc-tag{display:inline-block;font-size:12px;border:1px solid var(--rc-muted);border-radius:999px;padding:0 8px;margin-left:6px;color:var(--rc-muted)}
.rc details{border-top:1px dashed var(--rc-line);padding:8px 0}
.rc summary{cursor:pointer;font-weight:700;min-height:36px;display:flex;align-items:center}
.rc ol{padding-left:22px;margin:6px 0}
.rc .rc-ans{border-top:0;background:var(--rc-soft);border-radius:10px;padding:6px 12px;margin:6px 0 10px;font-size:15px}
.rc .rc-ans summary{font-weight:400;color:var(--rc-muted);font-size:14px}
.rc-review{display:grid;gap:8px;margin:8px 0}
.rc-review label{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:15px}
.rc-review select,.rc-review input{font:inherit;font-size:15px;padding:6px 8px;border:1px solid var(--rc-line);border-radius:8px;background:var(--rc-card);color:var(--rc-ink);min-height:40px}
.rc-review input{width:5em}
.rc-btns{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.rc-btns button{min-height:44px;border:0;border-radius:999px;padding:8px 16px;font:inherit;font-size:15px;font-weight:700;cursor:pointer;background:var(--rc-ink);color:var(--rc-card)}
.rc-btns button.rc-ghost{background:transparent;color:var(--rc-ink);border:2px solid var(--rc-line)}
.rc-note{font-size:13px;color:var(--rc-muted)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .rc{--rc-acc:#b7d43a}}
:root[data-theme="dark"] .rc{--rc-acc:#b7d43a}
</style>"""

JS = r"""<script>
(function(){var rc=document.currentScript.closest('.rc');if(!rc)return;var id=rc.dataset.id,card=JSON.parse(rc.querySelector('.rc-data').textContent);
function g(k){try{return localStorage.getItem('rc:'+id+':'+k)}catch(e){return null}}function s(k,v){try{localStorage.setItem('rc:'+id+':'+k,v)}catch(e){}}
var bs=rc.querySelectorAll('.rc-modes button'),tips=rc.querySelectorAll('.rc-tip[data-m]');
function pick(m){bs.forEach(function(b){b.setAttribute('aria-pressed',b.dataset.m===m)});tips.forEach(function(t){t.hidden=t.dataset.m!==m})}
bs.forEach(function(b){b.onclick=function(){pick(b.dataset.m);s('mode',b.dataset.m)}});var m=g('mode');if(m)pick(m);
var min=rc.querySelector('[data-k="min"]');if(min){min.value=g('min')||'';min.oninput=function(){s('min',min.value)}}
var start=rc.querySelector('.rc-start'),rev=rc.querySelector('.rc-review');
function ymd(x){return x.getFullYear()+'-'+('0'+(x.getMonth()+1)).slice(-2)+'-'+('0'+x.getDate()).slice(-2)}
function day(d,n){var p=d.split('-'),x=new Date(+p[0],p[1]-1,+p[2]);x.setDate(x.getDate()+n);return ymd(x)}
function showRev(){var d=g('start');if(!rev)return;rev.hidden=!d;if(start)start.textContent=d?'重新開始排複習':'開始排複習（今天讀完）';if(!d)return;
 rev.querySelector('[data-d="1"]').textContent=day(d,1);rev.querySelector('[data-d="7"]').textContent=day(d,7);
 rev.querySelectorAll('select').forEach(function(x){x.value=g(x.dataset.k)||''})}
if(start)start.onclick=function(){s('start',ymd(new Date()));s('d1','');s('d7','');showRev()};
if(rev)rev.querySelectorAll('select').forEach(function(x){x.onchange=function(){s(x.dataset.k,x.value)}});showRev();
var cp=rc.querySelector('.rc-copy');if(cp)cp.onclick=function(){
 var d=g('start'),L=[];var h=document.querySelector('h1');L.push('# '+(h?h.textContent.replace(/\s+/g,' ').trim():document.title));L.push('');
 L.push('- 來源｜'+location.href.split('#')[0]);L.push('- 我的問題｜'+card.question);L.push('- 首次定位｜'+(g('min')||'　')+' 分鐘');L.push('');
 L.push('| 欄位 | 筆記 |');L.push('|---|---|');
 L.push('| **Core Thesis（一句話核心）** | '+card.core+' |');
 L.push('| **Key Metrics（關鍵數據）** | '+(card.metrics.length?card.metrics.map(function(x){return x.v+'（'+x.basis+'；'+x.src+'）'}).join('<br>'):'未提供'+(card.metrics_note?'：'+card.metrics_note:''))+' |');
 L.push('| **Logic Flow（因果／流程）** | '+card.flow.join(' → ')+(card.flow_tag?'（'+card.flow_tag+'）':'')+' |');
 L.push('| **Cross-Domain Link（跨域應用）** | '+card.link.domain+'：'+card.link.change+' → '+card.link.observe+(card.link.tag?'（'+card.link.tag+'）':'')+' |');
 if(card.recall){L.push('');L.push('## 閉卷回想');L.push('');card.recall.forEach(function(r,i){L.push((i+1)+'. '+r.q)});L.push('');
  L.push('- 隔天 '+(d?day(d,1):'[日期]')+'｜'+(g('d1')||'　')+'/3');L.push('- 第 7 天 '+(d?day(d,7):'[日期]')+'｜'+(g('d7')||'　')+'/3');L.push('');
  L.push('> [!note]- 參考答案');card.recall.forEach(function(r,i){L.push('> '+(i+1)+'. '+r.a)})}
 var t=L.join('\n'),ok=function(){cp.textContent='已複製 ✓';setTimeout(function(){cp.textContent='複製成 Obsidian 筆記'},1800)};
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(ok,function(){fb(t)})}else fb(t);
 function fb(t){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');ok()}catch(e){alert(t)}a.remove()}};
})();
</script>"""


def block(card: dict, pid: str, guide_href: str) -> str:
    kw = '、'.join(f'「{esc(k)}」' for k in card.get('keywords', []))
    modes = ''.join(f'<button type="button" data-m="{m}" aria-pressed="false">{name}</button>' for m, name, _, _ in MODES)
    tips = ''.join(f'<div class="rc-tip" data-m="{m}" hidden><p>{esc(a).replace("{kw}", ("：" + kw) if kw else "")}</p><p>{esc(b)}</p></div>'
                   for m, _, a, b in MODES)
    if card.get('metrics'):
        met = '<ul>' + ''.join(f'<li><b>{esc(x["v"])}</b>｜{esc(x["basis"])}<br><small>出處：{esc(x["src"])}</small></li>' for x in card['metrics']) + '</ul>'
    else:
        met = f'<p>未提供{("：" + esc(card["metrics_note"])) if card.get("metrics_note") else ""}</p>'
    flow = '<div class="rc-flow">' + '<i>→</i>'.join(f'<span>{esc(x)}</span>' for x in card['flow']) + '</div>'
    if card.get('flow_tag'):
        flow += f'<p class="rc-note">標示：<span class="rc-tag">{esc(card["flow_tag"])}</span>（{"原文只支持相關，不能當成因果" if card["flow_tag"] == "相關" else "原文未交代機制"}）</p>'
    ln = card['link']
    link = f'<p><b>{esc(ln["domain"])}</b>：我會改「{esc(ln["change"])}」→ 觀察「{esc(ln["observe"])}」' + (f'<span class="rc-tag">{esc(ln["tag"])}</span>' if ln.get('tag') else '') + '</p>'
    if card.get('recall'):
        qs = ''.join(f'<li>{esc(r["q"])}<details class="rc-ans"><summary>參考答案（先自己答完再打開）</summary>{esc(r["a"])}</details></li>' for r in card['recall'])
        recall = f"""<details><summary>閉卷回想：蓋住上面，自己答兩題</summary>
<ol>{qs}</ol>
<p class="rc-note">只為值得長期使用的內容排複習：隔天和第 7 天各一次。每次先蓋住筆記，口述核心、重畫機制、說出一個適用條件，各 1 分。答不全時，只回看對應段落。</p>
<div class="rc-btns"><button type="button" class="rc-start rc-ghost">開始排複習（今天讀完）</button></div>
<div class="rc-review" hidden>
<label>隔天 <span data-d="1"></span>｜得分 <select data-k="d1"><option value="">未做</option><option>0</option><option>1</option><option>2</option><option>3</option></select> / 3</label>
<label>第 7 天 <span data-d="7"></span>｜得分 <select data-k="d7"><option value="">未做</option><option>0</option><option>1</option><option>2</option><option>3</option></select> / 3</label>
</div></details>"""
    else:
        recall = '<p class="rc-note">這篇主要供查閱，<b>不排複習</b>：找到需要的資料就可以停。</p>'
    data = {k: card.get(k) for k in ('question', 'core', 'metrics', 'metrics_note', 'flow', 'flow_tag', 'link', 'recall')}
    return f"""{START}<section class="rc" data-id="{esc(pid)}" aria-label="閱讀卡">{CSS}
<div class="rc-head"><b>閱讀卡</b><span>先選讀法，再讀全文</span></div>
<p class="rc-q">我讀這篇是為了回答：{esc(card['question'])}<small>選一種讀法，看看先讀哪裡、讀到哪裡可以停。<a href="{guide_href}">這套讀法是甚麼？</a></small></p>
<div class="rc-modes" role="group" aria-label="選擇讀法">{modes}</div>{tips}
<div class="rc-grid" id="rc-note">
<div class="rc-cell"><h4>一句話核心<span>Core Thesis</span></h4><p>{esc(card['core'])}</p></div>
<div class="rc-cell"><h4>關鍵數據<span>Key Metrics</span></h4>{met}</div>
<div class="rc-cell"><h4>因果／流程<span>Logic Flow</span></h4>{flow}</div>
<div class="rc-cell"><h4>跨域應用<span>Cross-Domain Link</span></h4>{link}</div>
</div>
<p class="rc-note"><label>首次找到答案花了 <input type="number" min="0" inputmode="numeric" data-k="min" style="width:4.5em;font:inherit;padding:2px 6px;border:1px solid var(--rc-line);border-radius:6px;background:var(--rc-card);color:var(--rc-ink)"> 分鐘（可不填）</label></p>
{recall}
<div class="rc-btns"><button type="button" class="rc-copy">複製成 Obsidian 筆記</button></div>
<p class="rc-note">Obsidian 是一個免費的筆記軟體；沒有安裝也可以把複製的內容貼到任何筆記或文件。</p>
<p class="rc-note">讀法選擇、分鐘數和複習分數只存在這部裝置的瀏覽器，不會上傳。四欄筆記依本頁內容整理；「待驗證」表示超出原文的推論。</p>
<script type="application/json" class="rc-data">{json.dumps(data, ensure_ascii=False).replace('</', '<\\/')}</script>
{JS}</section>{END}"""


def strip(text: str) -> str:
    """移除自動插入的閱讀卡與網站導覽條（用來和本機來源比較）。"""
    text = re.sub(re.escape(START) + r'.*?' + re.escape(END), '', text, flags=re.S)
    return re.sub(re.escape(SITE_START) + r'.*?' + re.escape(SITE_END), '', text, flags=re.S)


def site_strip(up: str, here: str) -> str:
    links = [('首頁', ''), ('學生學習', 'learn/'), ('教練科技', 'technology/'), ('教練研究', 'research/'), ('工具說明', 'skills/')]
    a = ''.join(f'<a href="{up}{h}" style="color:#e8f2ec;text-decoration:none;padding:6px 10px;border-radius:999px;{"background:#d7f24b;color:#16302a;" if h == here else ""}">{n}</a>' for n, h in links)
    return (f'{SITE_START}<div style="background:#11241f;padding:6px 10px;display:flex;gap:2px;overflow-x:auto;white-space:nowrap;'
            f'font:14px/1.4 -apple-system,BlinkMacSystemFont,\'PingFang TC\',sans-serif;position:relative;z-index:50" aria-label="網站導覽">'
            f'<span style="color:#d7f24b;font-weight:800;padding:6px 10px 6px 4px">badminton</span>{a}</div>{SITE_END}')


def insert(text: str, blk: str) -> str:
    """放在第一個 h1 之後；若 h1 在頁首 header 內，放在該 header 結束之後。"""
    text = re.sub(re.escape(START) + r'.*?' + re.escape(END), '', text, flags=re.S)
    i = text.find('</h1>')
    if i == -1:
        return text
    j = text.find('</header>', i)
    k = text.find('<h2', i)
    pos = j + len('</header>') if j != -1 and (k == -1 or j < k) else i + len('</h1>')
    m = re.match(r'\s*<p class="meta">.*?</p>', text[pos:], flags=re.S)   # 研究頁：日期行緊接標題
    if m:
        pos += m.end()
    return text[:pos] + blk + text[pos:]


def strip_cards(text: str) -> str:
    """只移除閱讀卡（網站已不顯示閱讀卡；四欄筆記改為整理文章時另外交給使用者）。"""
    return re.sub(re.escape(START) + r'.*?' + re.escape(END), '', text, flags=re.S)
