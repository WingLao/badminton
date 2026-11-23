// 羽毛球手指發力 v4：運動生物力學圖（肢段、受力、向量、時間序列）＋旁白＋動作音效
const TS = '202610151603';
const $ = (id) => document.getElementById(id);
const D2R = Math.PI / 180;
const lerp = (a, b, u) => a + (b - a) * u;
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
const smooth = (e0, e1, x) => { const u = clamp((x - e0) / (e1 - e0)); return u * u * (3 - 2 * u); };
const gauss = (u, c, w) => Math.exp(-(((u - c) / w) ** 2));
const COOL = [56, 189, 248], WARM = [255, 90, 31];
const col = (a) => `rgb(${COOL.map((v, i) => Math.round(lerp(v, WARM[i], clamp(a)))).join(',')})`;
const f0 = (v) => Math.round(v);

// ---------- 繪圖小工具 ----------
const T = (x, y, s, cls = 'lbl', anchor = 'middle') => `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${s}</text>`;
function chain(x, y, phi0, L, flex) {
  const pts = [[x, y]]; let phi = phi0; const dirs = [];
  L.forEach((l, i) => { phi += flex[i]; dirs.push(phi); const p = pts[pts.length - 1]; pts.push([p[0] + l * Math.cos(phi * D2R), p[1] + l * Math.sin(phi * D2R)]); });
  return { pts, dirs };
}
function seg(p, q, color, w = 12, op = 1) { return `<line x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}" stroke="${color}" stroke-width="${w}" stroke-linecap="round" opacity="${op}"/>`; }
function joint(p, r = 8, fill = '#0b1220') { return `<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${fill}" stroke="#e2e8f0" stroke-width="3"/>`; }
function arrow(x1, y1, x2, y2, color = '#ff5a1f', w = 4) {
  const a = Math.atan2(y2 - y1, x2 - x1), h = 9 + w * 1.6;
  const p1 = [x2 - h * Math.cos(a - 0.45), y2 - h * Math.sin(a - 0.45)], p2 = [x2 - h * Math.cos(a + 0.45), y2 - h * Math.sin(a + 0.45)];
  const xe = x2 - h * 0.7 * Math.cos(a), ye = y2 - h * 0.7 * Math.sin(a);
  return `<line x1="${x1}" y1="${y1}" x2="${xe}" y2="${ye}" stroke="${color}" stroke-width="${w}" stroke-linecap="round"/><polygon points="${x2},${y2} ${p1} ${p2}" fill="${color}"/>`;
}
function arcPath(cx, cy, r, a0, a1) {
  const p0 = [cx + r * Math.cos(a0 * D2R), cy + r * Math.sin(a0 * D2R)], p1 = [cx + r * Math.cos(a1 * D2R), cy + r * Math.sin(a1 * D2R)];
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0, sweep = a1 > a0 ? 1 : 0;
  return `M${p0} A${r} ${r} 0 ${large} ${sweep} ${p1}`;
}
// 關節角度弧：從「前一節延長線」轉到「下一節」
function angleArc(p, dPrev, dNext, r, label, lx, ly) {
  return `<path d="${arcPath(p[0], p[1], r, dPrev, dNext)}" class="arc"/>` + (label ? T(lx, ly, label, 'val') : '');
}
function octagon(cx, cy, R, rot = 0, hot = {}, opts = {}) {
  let s = '';
  for (let k = 0; k < 8; k++) {
    const a0 = (rot + k * 45 - 22.5) * D2R, a1 = (rot + k * 45 + 22.5) * D2R;
    const p0 = [cx + R * Math.cos(a0), cy + R * Math.sin(a0)], p1 = [cx + R * Math.cos(a1), cy + R * Math.sin(a1)];
    const h = hot[k] || 0;
    s += `<line x1="${p0[0]}" y1="${p0[1]}" x2="${p1[0]}" y2="${p1[1]}" stroke="${h ? col(h) : '#64748b'}" stroke-width="${h ? 8 : 4}" stroke-linecap="round"/>`;
  }
  const pts = [...Array(8)].map((_, k) => { const a = (rot + k * 45 + 22.5) * D2R; return `${cx + R * Math.cos(a)},${cy + R * Math.sin(a)}`; }).join(' ');
  return `<polygon points="${pts}" fill="#162231"/>` + s + (opts.label ? T(cx, cy + 6, opts.label, 'small') : '');
}
const faceNormal = (rot, k) => rot + k * 45; // 第 k 面的法向角（度）
function plot(x, y, w, h, fn, u, opts = {}) {
  let d = '';
  for (let i = 0; i <= 120; i++) { const t = i / 120, v = fn(t); d += `${i ? 'L' : 'M'}${x + t * w},${y + h - v * h}`; }
  const cur = fn(u);
  return `<path d="${d} L${x + w},${y + h} L${x},${y + h}Z" fill="${opts.fill || 'rgba(255,90,31,.12)'}"/><path d="${d}" fill="none" stroke="${opts.stroke || '#ff5a1f'}" stroke-width="3"/>` +
    (opts.cursor === false ? '' : `<line x1="${x + u * w}" y1="${y}" x2="${x + u * w}" y2="${y + h}" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="4 4"/><circle cx="${x + u * w}" cy="${y + h - cur * h}" r="6" fill="${col(cur)}" stroke="#fff" stroke-width="2"/>`);
}

// ---------- 共用動作曲線（u：0–1 一個循環；時間軸以觸球為 0 ms，畫面已放慢） ----------
const UC = 0.635, SPAN = 600;
const tms = (u) => (u - UC) * SPAN;
const gripGood = (u) => 0.12 + 0.86 * gauss(u, 0.6, 0.045);
const gripBad = (u) => 0.12 + 0.72 * smooth(0.08, 0.2, u) * (1 - smooth(0.86, 0.96, u)) + 0.12 * gauss(u, 0.6, 0.05);
const FLEX0 = [45, 92, 48], FLEXD = [12, 12, 12]; // 放鬆屈曲角與收緊增量（度，示意）

// 拍柄位置：由放鬆時手指「指環」的中心決定
function loopHandle(x, y, L, flex, halfW) {
  const { pts } = chain(x, y, -90, L, flex);
  const hc = [0, 1].map((k) => pts.reduce((sum, p) => sum + p[k], 0) / pts.length);
  let d = Infinity;
  for (let i = 0; i < 3; i++) { const [p, q] = [pts[i], pts[i + 1]], v = [q[0] - p[0], q[1] - p[1]], w = [hc[0] - p[0], hc[1] - p[1]];
    const t = clamp((v[0] * w[0] + v[1] * w[1]) / (v[0] ** 2 + v[1] ** 2)); d = Math.min(d, Math.hypot(w[0] - t * v[0], w[1] - t * v[1])); }
  return { hc, R: Math.max(12, d - halfW - 2) };
}
const G = (key, ctx, inner) => `<g class="${ctx.focus && ctx.focus.size ? (ctx.focus.has(key) ? 'hi' : 'dim') : ''}">${inner}</g>`;

// 時間序列圖（x 軸＝相對觸球時間 ms）
function tsPlot(x, y, w, h, u, series, o = {}) {
  let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#0d1726"/>`;
  (o.phases || []).forEach(([a, b, label, c]) => { s += `<rect x="${x + a * w}" y="${y}" width="${(b - a) * w}" height="${h}" fill="${c}"/>` + (label ? T(x + (a + b) / 2 * w, y + h + 22, label, 'small') : ''); });
  if (!o.noTicks) for (let t = -300; t <= 200; t += 100) {
    const xx = x + (t / SPAN + UC) * w; if (xx < x || xx > x + w) continue;
    s += `<line x1="${xx}" y1="${y}" x2="${xx}" y2="${y + h}" stroke="#1e2a3b"/>` + (o.xlabels === false ? '' : T(xx, y + h + 18, t > 0 ? `+${t}` : `${t}`, 'tick'));
  }
  if (o.contact !== false) { const cx = x + UC * w; s += `<line x1="${cx}" y1="${y - 6}" x2="${cx}" y2="${y + h}" stroke="#fbbf24" stroke-width="2" stroke-dasharray="6 5"/>` + T(cx, y - 10, '觸球', 'small warn'); }
  s += `<line x1="${x}" y1="${y + h}" x2="${x + w}" y2="${y + h}" class="axis"/><line x1="${x}" y1="${y}" x2="${x}" y2="${y + h}" class="axis"/>`;
  if (o.ylab) s += `<text x="${x - 16}" y="${y + h / 2}" class="small" text-anchor="middle" transform="rotate(-90 ${x - 16} ${y + h / 2})">${o.ylab}</text>`;
  if (o.xlab && o.xlabels !== false) s += T(x + w, y + h + 38, o.xlab, 'small', 'end');
  const lx = o.legendLeft ? x + 12 : x + w - 170, ly = o.legendY ?? y;
  series.forEach((sr, i) => {
    let d = ''; for (let k = 0; k <= 150; k++) { const t = k / 150; d += `${k ? 'L' : 'M'}${x + t * w},${y + h - clamp(sr.fn(t)) * h}`; }
    if (sr.fill) s += `<path d="${d} L${x + w},${y + h} L${x},${y + h}Z" fill="${sr.fill}"/>`;
    s += `<path d="${d}" fill="none" stroke="${sr.color}" stroke-width="${sr.w || 3}"${sr.dash ? ` stroke-dasharray="${sr.dash}"` : ''}/>`;
    const v = clamp(sr.fn(u)); s += `<circle cx="${x + u * w}" cy="${y + h - v * h}" r="5" fill="${sr.color}" stroke="#fff" stroke-width="1.5"/>`;
    if (o.legend !== false) s += `<line x1="${lx}" y1="${ly + 16 + i * 20}" x2="${lx + 22}" y2="${ly + 16 + i * 20}" stroke="${sr.color}" stroke-width="4"/>` + T(lx + 28, ly + 21 + i * 20, sr.label, 'small', 'start');
  });
  return s + `<line x1="${x + u * w}" y1="${y}" x2="${x + u * w}" y2="${y + h}" stroke="#e2e8f0" stroke-width="1.2" stroke-dasharray="3 4"/>`;
}

// 手指矢狀面肢段（MCP–PIP–DIP）＋拍柄截面
function fingerFig(M, s, a, withAngles) {
  const k = s / 1.6, palm = [M[0] - 140 * k, M[1] + 36 * k];
  const L = [90, 55, 40].map((v) => v * s), flex = FLEX0.map((v, i) => v + FLEXD[i] * a);
  const c = chain(M[0], M[1], -90, L, flex);
  const { hc, R } = loopHandle(M[0], M[1], L, FLEX0, 7 * k);
  const pad = [lerp(c.pts[2][0], c.pts[3][0], 0.5), lerp(c.pts[2][1], c.pts[3][1], 0.5)];
  const dv = [hc[0] - pad[0], hc[1] - pad[1]], dl = Math.hypot(...dv), alen = 10 + 55 * a * k;
  const sc = col(a);
  let body = octagon(hc[0], hc[1], R, 0, {}, { label: withAngles ? '拍柄' : '' }) + seg(palm, M, '#94a3b8', 26 * k)
    + seg(c.pts[0], c.pts[1], sc, 14 * k) + seg(c.pts[1], c.pts[2], sc, 13 * k) + seg(c.pts[2], c.pts[3], sc, 12 * k)
    + c.pts.slice(0, 3).map((p) => joint(p, 8 * k)).join('') + joint(c.pts[3], 5, '#e2e8f0');
  if (a > 0.3) body += arrow(pad[0] - dv[0] / dl * (alen + 8), pad[1] - dv[1] / dl * (alen + 8), pad[0] - dv[0] / dl * 8, pad[1] - dv[1] / dl * 8, '#ff5a1f', 3 + 3 * a);
  let angles = '';
  if (withAngles) {
    const palmDir = Math.atan2(M[1] - palm[1], M[0] - palm[0]) / D2R;
    angles = angleArc(c.pts[0], palmDir, c.dirs[0], 30, `θ<tspan class="sub">MCP</tspan> ${f0(flex[0])}°`, c.pts[0][0] - 74, c.pts[0][1] - 6)
      + angleArc(c.pts[1], c.dirs[0], c.dirs[1], 26, `θ<tspan class="sub">PIP</tspan> ${f0(flex[1])}°`, c.pts[1][0] + 4, c.pts[1][1] - 34)
      + angleArc(c.pts[2], c.dirs[1], c.dirs[2], 22, `θ<tspan class="sub">DIP</tspan> ${f0(flex[2])}°`, c.pts[2][0] + 74, c.pts[2][1] + 4);
  }
  return { body, angles };
}

// 上肢側面肢段（肘–腕–手–拍）
function armSide(x, y, u, bad, opts = {}) {
  const k = opts.k || 1, a = (bad ? gripBad : gripGood)(u);
  const back = 1 - smooth(0.78, 1, u);
  const wrist = (bad ? lerp(-38, 36, smooth(0.45, 0.65, u)) : lerp(-10, 8, smooth(0.5, 0.66, u))) * back + (bad ? -38 : -10) * (1 - back);
  const fore = bad ? 0 : lerp(-8, 6, smooth(0.4, 0.62, u));
  const E = [x, y], Wp = [x + 170 * k * Math.cos(fore * D2R), y + 170 * k * Math.sin(fore * D2R)];
  const hd = fore + wrist, Hp = [Wp[0] + 58 * k * Math.cos(hd * D2R), Wp[1] + 58 * k * Math.sin(hd * D2R)];
  const rd = hd - 25 + (bad ? 0 : 16 * a), Rk = [Hp[0] + 150 * k * Math.cos(rd * D2R), Hp[1] + 150 * k * Math.sin(rd * D2R)];
  const hx = Rk[0] + 26 * k * Math.cos(rd * D2R), hy = Rk[1] + 26 * k * Math.sin(rd * D2R);
  let s = seg(E, Wp, '#94a3b8', 18 * Math.max(k, 0.7)) + seg(Wp, Hp, col(bad ? 0.2 : a), 14 * Math.max(k, 0.7)) + seg(Hp, Rk, '#cbd5e1', 5);
  s += `<ellipse cx="${hx}" cy="${hy}" rx="${28 * k}" ry="${20 * k}" transform="rotate(${rd} ${hx} ${hy})" fill="none" stroke="#0ea5e9" stroke-width="4"/>`;
  s += joint(E, 9) + joint(Wp, 9) + joint(Hp, 6) + `<path d="${arcPath(Wp[0], Wp[1], 34, fore, hd)}" class="arc"/>`;
  s += T(Wp[0], Wp[1] + 58, `腕角 ${f0(Math.abs(wrist))}°`, Math.abs(wrist) > 20 ? 'val bad' : 'val');
  if (!opts.mini) s += T(E[0], E[1] + 40, '肘', 'small') + T(Wp[0], Wp[1] - 20, '腕', 'small');
  return s;
}

const SCENES = {};

// 01 時序：肢段＋力–時間＋角度–時間（同一時間軸）
SCENES.timing = (u, ctx) => {
  const bad = ctx.variant === 'bad', g = bad ? gripBad : gripGood, a = g(u);
  const angN = (k) => (t) => (FLEX0[k] + FLEXD[k] * g(t) - 30) / 80; // 30°–110° → 0–1
  if (ctx.mini) {
    const f = fingerFig([105, 175], 1.0, a, false);
    return f.body + tsPlot(225, 50, 235, 170, u, [{ fn: g, color: '#ff5a1f', label: '', fill: 'rgba(255,90,31,.14)' }], { legend: false, xlabels: false }) + T(110, 285, `握力 ${f0(a * 100)}%`, 'val');
  }
  const f = fingerFig([190, 285], 1.5, a, true);
  const flex = FLEX0.map((v, i) => v + FLEXD[i] * a);
  const read = T(60, 470, `θMCP ${f0(flex[0])}°　θPIP ${f0(flex[1])}°　θDIP ${f0(flex[2])}°`, 'val', 'start') + T(60, 505, `握力 ${f0(a * 100)}%（相對峰值）　t = ${tms(u) > 0 ? '+' : ''}${f0(tms(u))} ms`, 'val', 'start');
  const force = tsPlot(480, 60, 440, 165, u, [{ fn: g, color: '#ff5a1f', label: '握力（% 峰值）', fill: 'rgba(255,90,31,.13)' }], { ylab: '握力', xlabels: false });
  const pkx = 480 + 0.6 * 440, pky = 60 + 165 - 0.98 * 165;
  const peak = `<circle cx="${pkx}" cy="${pky}" r="9" fill="none" stroke="#fbbf24" stroke-width="3"/>` + T(pkx - 16, pky + 30, `峰值 t ≈ ${f0(tms(0.6))} ms`, 'small warn', 'end');
  const angles = tsPlot(480, 290, 440, 150, u, [
    { fn: angN(0), color: '#a78bfa', label: 'θMCP' }, { fn: angN(1), color: '#38bdf8', label: 'θPIP' }, { fn: angN(2), color: '#34d399', label: 'θDIP' }],
    { ylab: '屈曲角', xlab: '相對觸球時間（ms）', legendLeft: true, legendY: 290 + 150 * 0.3 }) + T(925, 300, '110°', 'tick', 'end') + T(925, 438, '30°', 'tick', 'end');
  return G('finger', ctx, f.body) + G('angles', ctx, f.angles + angles) + G('force', ctx, force) + G('peak', ctx, peak) + read;
};
SCENES.timing.events = [{ u: 0.5, type: 'tick' }, { u: 0.6, type: 'snap' }, { u: 0.72, type: 'tick' }];

// 02 正手：握拍受力圖（槓桿）＋ τ、ω 時間曲線
const LEVER = [{ n: '中指', d: 2.5, w: 1 }, { n: '無名指', d: 4.0, w: 0.85 }, { n: '小指', d: 5.5, w: 0.75 }];
const tauN = (u) => 0.03 + 0.95 * (gripGood(u) - 0.12) / 0.86;
const omegaN = (u) => 0.08 + 0.9 * gauss(u, UC, 0.06);
function leverFig(x0, y0, u, ctx, k = 1) {
  const a = gripGood(u), P = [x0 + 240 * k, y0], px = 26 * k;
  const phi = 12 * smooth(0.45, 0.66, u) * (1 - smooth(0.8, 1, u));
  const fs = LEVER.map((f) => ({ ...f, f: 0.1 + (a - 0.1) * f.w, x: P[0] - f.d * px }));
  let rot = `<rect x="${x0}" y="${y0 - 13 * k}" width="${270 * k}" height="${26 * k}" rx="5" fill="#1f2937" stroke="#64748b" stroke-width="2"/>`
    + `<rect x="${x0 - 6 * k}" y="${y0 - 15 * k}" width="${8 * k}" height="${30 * k}" rx="2" fill="#ff5a1f"/>`
    + seg([x0 + 270 * k, y0], [x0 + 540 * k, y0], '#cbd5e1', 5)
    + `<ellipse cx="${x0 + 585 * k}" cy="${y0}" rx="${46 * k}" ry="${11 * k}" fill="none" stroke="#0ea5e9" stroke-width="5"/>`;
  let forces = '';
  fs.forEach((f) => {
    const len = 18 + 70 * f.f * k;
    forces += arrow(f.x, y0 + 13 * k + len + 6, f.x, y0 + 15 * k, col(f.f), 3 + 4 * f.f) + T(f.x, y0 + 13 * k + len + 26, `F<tspan class="sub">${f.n}</tspan>`, 'small');
  });
  rot += `<polygon points="${P[0]},${y0 - 14 * k} ${P[0] - 11 * k},${y0 - 34 * k} ${P[0] + 11 * k},${y0 - 34 * k}" fill="#fbbf24"/>`;
  let dims = '';
  fs.forEach((f, i) => { const yy = y0 + 150 * k + i * 22 * k; dims += `<line x1="${f.x}" y1="${yy}" x2="${P[0]}" y2="${yy}" stroke="#94a3b8" stroke-width="1.5"/><line x1="${f.x}" y1="${yy - 5}" x2="${f.x}" y2="${yy + 5}" stroke="#94a3b8"/>` + T(f.x - 8, yy + 5, `d=${f.d}`, 'tick', 'end'); });
  dims += `<line x1="${P[0]}" y1="${y0 + 18 * k}" x2="${P[0]}" y2="${y0 + 200 * k}" stroke="#fbbf24" stroke-dasharray="4 4"/>`;
  const head = [x0 + 585 * k, y0];
  const om = omegaN(u);
  const arcS = `<path d="${arcPath(P[0], P[1], 345 * k, -10, 14)}" fill="none" stroke="#38bdf8" stroke-width="${2 + 4 * om}" stroke-dasharray="7 6"/>` + T(head[0], head[1] + 44 * k, `ω 拍頭 ${f0(om * 100)}%`, 'val');
  const tau = fs.reduce((s2, f) => s2 + f.f * f.d, 0) / LEVER.reduce((s2, f) => s2 + f.w * f.d, 0);
  return { rot: `<g transform="rotate(${phi} ${P[0]} ${P[1]})">${rot}${forces}</g>`, dims, arcS, tau, P,
    label: T(P[0], y0 - 44 * k, '支點：拇指＋食指（V）', 'small warn') };
}
SCENES.forehand = (u, ctx) => {
  const bad = ctx.variant === 'bad';
  if (ctx.mini) return armSide(80, 160, u, bad, { mini: true }) + T(240, 280, bad ? '手指不出力，靠大幅折腕' : '手指力矩＋前臂，腕角小', 'small');
  const L = leverFig(80, 150, u, ctx);
  const tb = `<rect x="560" y="290" width="220" height="14" rx="7" fill="#1e293b"/><rect x="560" y="290" width="${220 * clamp(L.tau)}" height="14" rx="7" fill="${col(L.tau)}"/>`
    + T(560, 280, `τ = ΣF·d　${f0(clamp(L.tau) * 100)}%（相對峰值）`, 'val', 'start') + T(560, 324, 'd：到支點的距離，cm（示意）', 'tick', 'start');
  const plot = tsPlot(80, 350, 840, 130, u, [{ fn: tauN, color: '#ff5a1f', label: '手指力矩 τ', fill: 'rgba(255,90,31,.12)' }, { fn: omegaN, color: '#38bdf8', label: '拍頭角速度 ω' }], { ylab: '相對值', xlab: '相對觸球時間（ms）' });
  return G('fbd', ctx, L.rot + L.label) + G('forces', ctx, L.dims) + G('torque', ctx, tb + L.arcS) + G('plot', ctx, plot);
};
SCENES.forehand.events = [{ u: 0.6, type: 'snap' }];

// 03 反手：拇指推力向量與擊球方向的分解
function thumbChain(cx, cy, R, k, a) {
  const n = faceNormal(0, k) * D2R, ap = R * Math.cos(22.5 * D2R), nOut = [Math.cos(n), Math.sin(n)], t = [-nOut[1], nOut[0]];
  const P = [cx + nOut[0] * (ap + 11 - 5 * a), cy + nOut[1] * (ap + 11 - 5 * a)];
  const I = [P[0] - t[0] * 22, P[1] - t[1] * 22], Tp = [P[0] + t[0] * 15, P[1] + t[1] * 15];
  const Mj = [I[0] - t[0] * 24 + nOut[0] * 30, I[1] - t[1] * 24 + nOut[1] * 30], B = [Mj[0] + nOut[0] * 40 - t[0] * 18, Mj[1] + nOut[1] * 40 - t[1] * 18];
  const c = col(a);
  return seg(B, Mj, c, 15) + seg(Mj, I, c, 13) + seg(I, Tp, c, 12) + joint(B, 6) + joint(Mj, 6) + joint(I, 6);
}
function vecPanel(cx, cy, u, thumbK, hitDeg, R, opts = {}) {
  const a = gripGood(u);
  const pushDeg = faceNormal(0, thumbK) + 180;
  let th = ((pushDeg - hitDeg) % 360 + 540) % 360 - 180; th = Math.abs(th);
  let o = octagon(cx, cy, R, 0, { [thumbK]: a });
  const fd = (hitDeg + 90) * D2R; // 拍面線＝垂直擊球方向
  o += `<line x1="${cx - Math.cos(fd) * (R + 30)}" y1="${cy - Math.sin(fd) * (R + 30)}" x2="${cx + Math.cos(fd) * (R + 30)}" y2="${cy + Math.sin(fd) * (R + 30)}" stroke="#0ea5e9" stroke-width="3" stroke-dasharray="7 6"/>`;
  o += thumbChain(cx, cy, R, thumbK, a);
  const hd = hitDeg * D2R, pd = pushDeg * D2R, L = (R + 40) * (0.25 + 0.75 * a);
  let v = arrow(cx, cy, cx + Math.cos(hd) * (R + 55), cy + Math.sin(hd) * (R + 55), '#34d399', 4);
  if (!opts.mini) v += T(cx + Math.cos(hd) * (R + 78), cy + Math.sin(hd) * (R + 78) + 5, '擊球方向', 'small');
  const pe = [cx + Math.cos(pd) * L, cy + Math.sin(pd) * L], proj = L * Math.cos(th * D2R), pj = [cx + Math.cos(hd) * proj, cy + Math.sin(hd) * proj];
  v += arrow(cx, cy, pe[0], pe[1], '#ff5a1f', 5);
  if (th > 1) v += `<line x1="${pj[0]}" y1="${pj[1]}" x2="${pe[0]}" y2="${pe[1]}" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 4"/>` + seg([cx, cy], pj, 'rgba(52,211,153,.55)', 9);
  if (th > 1) v += `<path d="${arcPath(cx, cy, 34, Math.min(hitDeg, pushDeg > 180 ? pushDeg - 360 : pushDeg), Math.max(hitDeg, pushDeg > 180 ? pushDeg - 360 : pushDeg))}" class="arc"/>`;
  const eff = Math.cos(th * D2R);
  const read = T(cx, cy + R + 92, `θ = ${f0(th)}°　有效分量 F·cosθ = ${f0(eff * 100)}%`, eff < 0.9 ? 'val bad' : 'val');
  return { o, v, read };
}
SCENES.backhand = (u, ctx) => {
  if (ctx.mini) {
    const bad = ctx.variant === 'bad', p = vecPanel(240, 135, u, bad ? 4 : 3, -45, 56, { mini: true });
    return p.o + p.v + T(240, 285, bad ? '拍面已轉，拇指留在寬面：θ 45°、71%' : '拇指改貼斜面：θ 0°、100%', 'small');
  }
  const A = vecPanel(240, 235, u, 4, 0, 70), B = vecPanel(700, 235, u, 3, -45, 70);
  return G('front', ctx, A.o + T(240, 82, '身前反手｜拇指貼寬面', 'lbl') + A.read) + G('back', ctx, B.o + T(700, 82, '側後方反手｜拍面轉 45°，拇指貼斜面', 'lbl') + B.read)
    + G('vectors', ctx, A.v + B.v) + T(480, 520, '從拍柄底往上看；綠＝擊球方向、橘＝拇指推力、藍虛線＝拍面（示意）', 'small');
};
SCENES.backhand.events = [{ u: 0.6, type: 'snap' }];

// 04 動力鏈：前臂截面＋側面腕角＋各肢段角速度–時間
const pronOf = (u) => -45 + 85 * smooth(0.4, 0.58, u) - 85 * smooth(0.75, 1, u);
const CHAIN = [['肩內旋', 0.3, '#a78bfa'], ['肘伸展', 0.4, '#60a5fa'], ['前臂旋前', 0.49, '#34d399'], ['腕', 0.555, '#fbbf24'], ['手指', 0.6, '#ff5a1f']];
SCENES.rotation = (u, ctx) => {
  const bad = ctx.variant === 'bad';
  if (ctx.mini) return armSide(80, 160, u, bad, { mini: true }) + T(240, 280, bad ? '拍面轉向靠折腕' : '拍面轉向靠前臂旋前', 'small');
  const p = pronOf(u), cx = 160, cy = 190, U = [cx - 26, cy + 14];
  const ang = (-40 - p) * D2R, Rd = [U[0] + 60 * Math.cos(ang), U[1] + 60 * Math.sin(ang)];
  let ax = `<ellipse cx="${cx}" cy="${cy}" rx="88" ry="64" fill="#162231" stroke="#64748b" stroke-width="3"/>`
    + `<path d="${arcPath(U[0], U[1], 60, 5, -80)}" fill="none" stroke="#334155" stroke-width="9" stroke-linecap="round"/>`
    + seg(U, Rd, '#475569', 4) + `<circle cx="${U[0]}" cy="${U[1]}" r="15" fill="#94a3b8"/><circle cx="${Rd[0]}" cy="${Rd[1]}" r="15" fill="${col(clamp((p + 10) / 50))}"/>`;
  const pa = (-90 + p) * D2R;
  ax += arrow(cx, cy, cx + 70 * Math.cos(pa), cy + 70 * Math.sin(pa), '#38bdf8', 4) + T(cx + 88 * Math.cos(pa), cy + 88 * Math.sin(pa) + 5, '掌心', 'small');
  ax += T(U[0], U[1] + 38, '尺骨', 'small') + T(Rd[0] + 30, Rd[1] - 14, '橈骨', 'small') + T(cx, 66, '前臂截面（腕端視角）', 'lbl') + T(cx, 292, p >= 0 ? `旋前 ${f0(p)}°` : `旋後 ${f0(-p)}°`, 'big');
  const side = armSide(330, 180, u, false, { k: 0.6 }) + T(450, 66, '側面：腕角小幅變化', 'lbl');
  const plot = tsPlot(80, 330, 840, 150, u, CHAIN.map(([n, c, color]) => ({ fn: (t) => 0.92 * gauss(t, c, 0.055), color, label: n })), { ylab: '角速度（標準化）', xlab: '相對觸球時間（ms）', legendLeft: true });
  let peaks = '';
  CHAIN.forEach(([n, c, color]) => { const x = 80 + c * 840, y = 330 + 150 - 0.92 * 150; peaks += `<circle cx="${x}" cy="${y}" r="5" fill="none" stroke="${color}" stroke-width="2"/>` + T(x, y - 10, `${f0(tms(c))}`, 'tick'); });
  peaks += arrow(640, 258, 900, 258, '#94a3b8', 2) + T(770, 250, '峰值順序：近端 → 遠端', 'small');
  return G('axial', ctx, ax) + G('side', ctx, side) + G('chain', ctx, plot) + G('peaks', ctx, peaks) + T(920, 66, '峰值時間為教學示意', 'tick', 'end');
};
SCENES.rotation.events = [{ u: 0.49, type: 'tick' }, { u: 0.6, type: 'snap' }];

// 05 網前：拍面角 α、出球角 β 與 α–β 關係
const alphaOf = (u, bad) => (bad ? 30 : 7) * Math.sin(u * Math.PI * 2);
const betaOf = (al) => al + 4; // 低速網前球：出球大致沿拍面法線（示意）
function netGeom(x0, y0, u, bad, s = 1, labels = true) {
  const al = alphaOf(u, bad), be = betaOf(al), H = [x0 + 140 * s, y0], netX = x0 + 290 * s;
  let o = `<line x1="${netX}" y1="${y0 - 40 * s}" x2="${netX}" y2="${y0 + 170 * s}" stroke="#e2e8f0" stroke-width="3"/>` + (labels ? T(netX, y0 + 192 * s, '球網', 'small') : '');
  const fdir = (90 - al) * D2R; // 拍面線方向（α＝向上仰角）
  const fa = [H[0] + Math.cos(fdir) * 52 * s, H[1] - Math.sin(fdir) * 52 * s], fb = [H[0] - Math.cos(fdir) * 52 * s, H[1] + Math.sin(fdir) * 52 * s];
  o += seg([H[0] - 70 * s, H[1] + 150 * s], H, '#cbd5e1', 5 * s) + seg(fa, fb, '#0ea5e9', 9 * s);
  o += `<line x1="${H[0]}" y1="${H[1] - 70 * s}" x2="${H[0]}" y2="${H[1] + 70 * s}" stroke="#334155" stroke-dasharray="4 5"/>`;
  const out = -be * D2R, len = 230 * s;
  o += `<line x1="${H[0]}" y1="${H[1]}" x2="${H[0] + len}" y2="${H[1]}" stroke="#334155" stroke-dasharray="4 5"/>`;
  o += arrow(H[0], H[1], H[0] + Math.cos(out) * len * 0.6, H[1] + Math.sin(out) * len * 0.6, Math.abs(al) > 8 ? '#ef4444' : '#fbbf24', 4);
  const kk = (u * 1.5) % 1, bx = H[0] + Math.cos(out) * len * kk, by = H[1] + Math.sin(out) * len * kk + 60 * s * kk * kk;
  o += `<circle cx="${bx}" cy="${by}" r="${7 * s}" fill="#fff"/>`;
  if (labels) o += `<path d="${arcPath(H[0], H[1], 40 * s, -90, -90 - al)}" class="arc"/>` + T(H[0] - 34 * s, H[1] - 80 * s, `α ${al >= 0 ? '+' : ''}${f0(al)}°`, Math.abs(al) > 8 ? 'val bad' : 'val')
    + `<path d="${arcPath(H[0], H[1], 70 * s, 0, -be)}" class="arc"/>` + T(H[0] + 110 * s, H[1] - 26 * s - Math.max(0, be) * 1.4, `β ${be >= 0 ? '+' : ''}${f0(be)}°`, 'val');
  return { o, al, be };
}
function abPlot(x, y, w, h, al, be, bad) {
  const X = (a) => x + (a + 30) / 60 * w, Y = (b) => y + h - (b + 30) / 60 * h;
  let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#0d1726"/><rect x="${X(-8)}" y="${y}" width="${X(8) - X(-8)}" height="${h}" fill="rgba(52,211,153,.14)"/>`;
  s += `<line x1="${X(-30)}" y1="${Y(betaOf(-30))}" x2="${X(30)}" y2="${Y(betaOf(30))}" stroke="#fbbf24" stroke-width="3"/>`;
  s += `<line x1="${x}" y1="${Y(0)}" x2="${x + w}" y2="${Y(0)}" class="axis"/><line x1="${X(0)}" y1="${y}" x2="${X(0)}" y2="${y + h}" class="axis"/>`;
  [-30, -15, 15, 30].forEach((t) => { s += T(X(t), Y(0) + 18, `${t}`, 'tick') + T(X(0) - 8, Y(t) + 4, `${t}`, 'tick', 'end'); });
  s += `<circle cx="${X(al)}" cy="${Y(be)}" r="8" fill="${Math.abs(al) > 8 ? '#ef4444' : '#fbbf24'}" stroke="#fff" stroke-width="2"/>`;
  s += T(x + w, y + h + 26, '拍面角 α（°）', 'small', 'end') + T(x + 8, y + 18, '出球角 β（°）', 'small', 'start') + T(X(0), y + h - 10, '可控範圍 ±8°', 'small');
  return s;
}
SCENES.net = (u, ctx) => {
  const bad = ctx.variant === 'bad';
  if (ctx.mini) { const n = netGeom(20, 120, u, bad, 0.7, false); return n.o + abPlot(300, 40, 160, 160, n.al, n.be, bad) + T(240, 285, bad ? '手腕大擺：α 超出範圍' : 'α 只調幾度', 'small'); }
  const n = netGeom(40, 250, u, false);
  return G('geom', ctx, n.o + T(220, 70, '網前：拍面角與出球角', 'lbl')) + G('plot', ctx, abPlot(580, 90, 330, 330, n.al, n.be, false) + T(745, 70, 'α–β 關係（示意）', 'lbl'));
};
SCENES.net.events = [{ u: 0.25, type: 'tap' }, { u: 0.75, type: 'tap' }];

// 06 換握：握力與拍柄轉角（同一時間軸）
function changeState(u, bad) {
  const rotMax = bad ? -10 : -50;
  const rot = rotMax * (smooth(0.27, 0.43, u) - smooth(0.74, 0.9, u));
  const relax = (smooth(0.22, 0.27, u) - smooth(0.43, 0.48, u)) + (smooth(0.69, 0.74, u) - smooth(0.9, 0.95, u));
  const tension = clamp((bad ? 0.8 : 0.4 - 0.3 * relax) + (bad ? 0.1 : 0.55) * (gauss(u, 0.12, 0.03) + gauss(u, 0.6, 0.03)));
  return { rot, tension };
}
function changeFig(cx, cy, R, st, mini) {
  const thumbA = 205, indexA = 330;
  const nearest = (a) => { let best = 0, bd = 999; for (let k = 0; k < 8; k++) { const d = Math.abs(((faceNormal(st.rot, k) - a) % 360 + 540) % 360 - 180); if (d < bd) { bd = d; best = k; } } return best; };
  const tk = nearest(thumbA);
  let oc = octagon(cx, cy, R, st.rot, { [tk]: 0.3 + 0.7 * st.tension, [nearest(indexA)]: 0.2 + 0.5 * st.tension });
  [0, 4].forEach((k) => { const a = faceNormal(st.rot, k) * D2R; oc += T(cx + Math.cos(a) * (R - 30), cy + Math.sin(a) * (R - 30) + 5, '寬面', 'tick'); });
  const dot = (a, label) => { const r = R + (mini ? 13 : 20), x = cx + Math.cos(a * D2R) * r, y = cy + Math.sin(a * D2R) * r;
    return `<circle cx="${x}" cy="${y}" r="${mini ? 9 : 13}" fill="${col(st.tension)}" stroke="#fff" stroke-width="2"/>` + (mini ? '' : T(x + (Math.cos(a * D2R) > 0 ? 38 : -38), y + 6, label, 'small')); };
  return { oc: oc + dot(thumbA, '拇指') + dot(indexA, '食指'), wide: tk % 4 === 0 };
}
SCENES.change = (u, ctx) => {
  const bad = ctx.variant === 'bad', st = changeState(u, bad);
  if (ctx.mini) {
    const f = changeFig(300, 140, 66, st, true);
    return `<rect x="70" y="50" width="22" height="180" rx="8" fill="#1e293b"/><rect x="70" y="${50 + 180 * (1 - st.tension)}" width="22" height="${180 * st.tension}" rx="8" fill="${col(st.tension)}"/>` + f.oc + T(240, 285, bad ? '一直握緊：拍柄轉不動' : '先鬆、再轉、再扣', 'small');
  }
  const f = changeFig(270, 190, 95, st, false);
  const phase = u < 0.25 ? '正手握' : u < 0.45 ? '放鬆・轉動' : u < 0.72 ? '反手握' : u < 0.92 ? '放鬆・轉回' : '正手握';
  const plot = tsPlot(80, 345, 840, 125, u, [{ fn: (t) => changeState(t, false).tension, color: '#ff5a1f', label: '握力', fill: 'rgba(255,90,31,.1)' }, { fn: (t) => Math.abs(changeState(t, false).rot) / 50, color: '#38bdf8', label: '拍柄轉角' }],
    { contact: false, noTicks: true, phases: [[0, 0.25, '正手握', 'rgba(255,90,31,.05)'], [0.25, 0.45, '放鬆・轉動', 'rgba(56,189,248,.09)'], [0.45, 0.72, '反手握', 'rgba(255,90,31,.05)'], [0.72, 0.92, '放鬆・轉回', 'rgba(56,189,248,.09)']], ylab: '相對值' });
  return G('octagon', ctx, f.oc + T(270, 62, `拇指在：${f.wide ? '寬面' : '斜面'}`, 'val warm') + T(270, 322, `轉角 ${f0(Math.abs(st.rot))}°（示例）`, 'small'))
    + `<rect x="560" y="120" width="300" height="16" rx="8" fill="#1e293b"/><rect x="560" y="120" width="${300 * st.tension}" height="16" rx="8" fill="${col(st.tension)}"/>` + T(560, 108, `握力 ${f0(st.tension * 100)}%`, 'val', 'start')
    + T(710, 200, phase, 'big') + G('plot', ctx, plot);
};
SCENES.change.events = [{ u: 0.12, type: 'snap' }, { u: 0.27, type: 'tick' }, { u: 0.6, type: 'snap' }, { u: 0.74, type: 'tick' }];

// ---------- 聲音（Web Audio 即時生成） ----------
class Sound {
  constructor() { this.ctx = null; this.fx = true; this.bgmOn = false; this.vol = 0.4; }
  init() {
    if (this.ctx) return;
    const c = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.out = c.createGain(); this.out.connect(c.destination);
    this.bgm = c.createGain(); this.bgm.gain.value = 0; this.bgm.connect(this.out);
    this.lp = c.createBiquadFilter(); this.lp.type = 'lowpass'; this.lp.frequency.value = 1300; this.lp.connect(this.bgm);
    this.noise = c.createBuffer(1, c.sampleRate * 0.5, c.sampleRate); const d = this.noise.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    this.next = c.currentTime + 0.1; this.bar = 0;
    setInterval(() => this.loop(), 200);
  }
  setBgm(on) { this.bgmOn = on; this.applyBgm(); }
  duck(on) { this.ducked = on; this.applyBgm(); }
  applyBgm() { if (this.ctx) this.bgm.gain.setTargetAtTime(this.bgmOn ? this.vol * (this.ducked ? 0.35 : 0.8) : 0, this.ctx.currentTime, 0.3); }
  loop() { // 柔和和弦墊底，每 4 秒換一個和弦
    const c = this.ctx; if (c.currentTime + 0.5 < this.next) return;
    const chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 64]];
    const t = this.next, notes = chords[this.bar++ % 4];
    for (const n of notes) { const o = c.createOscillator(), g = c.createGain(); o.type = 'triangle'; o.frequency.value = 440 * 2 ** ((n - 81) / 12);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.05, t + 1); g.gain.linearRampToValueAtTime(0, t + 4.4); o.connect(g).connect(this.lp); o.start(t); o.stop(t + 4.5); }
    this.next += 4;
  }
  play(type) {
    if (!this.ctx || !this.fx) return;
    const c = this.ctx, t = c.currentTime + 0.005;
    if (type === 'snap') { // 收緊瞬間：清脆擊發
      const o = c.createOscillator(), g = c.createGain(); o.type = 'square'; o.frequency.setValueAtTime(2500, t); o.frequency.exponentialRampToValueAtTime(1100, t + 0.06);
      g.gain.setValueAtTime(0.14, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.09); o.connect(g).connect(this.out); o.start(t); o.stop(t + 0.1);
      const s = c.createBufferSource(), f = c.createBiquadFilter(), gn = c.createGain(); s.buffer = this.noise; f.type = 'bandpass'; f.frequency.value = 4000;
      gn.gain.setValueAtTime(0.45, t); gn.gain.exponentialRampToValueAtTime(0.001, t + 0.035); s.connect(f).connect(gn).connect(this.out); s.start(t, 0, 0.04);
      const k = c.createOscillator(), gk = c.createGain(); k.frequency.setValueAtTime(170, t); k.frequency.exponentialRampToValueAtTime(60, t + 0.08);
      gk.gain.setValueAtTime(0.3, t); gk.gain.exponentialRampToValueAtTime(0.001, t + 0.1); k.connect(gk).connect(this.out); k.start(t); k.stop(t + 0.12);
    } else { // tick：階段轉換的柔和提示；tap：網前輕觸
      const o = c.createOscillator(), g = c.createGain(); o.type = 'sine'; o.frequency.value = type === 'tap' ? 1320 : 660;
      g.gain.setValueAtTime(type === 'tap' ? 0.12 : 0.08, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.12); o.connect(g).connect(this.out); o.start(t); o.stop(t + 0.14);
    }
  }
}

// ---------- 主程式 ----------
(async function main() {
  const [data, manifest] = await Promise.all([fetch(`content_${TS}.json`).then((r) => r.json()), fetch(`audio_manifest_${TS}.json`).then((r) => r.json())]);
  const chapters = data.chapters, videos = data.videos;
  const sound = new Sound(), voice = new Audio();
  let cur = 0, line = -1, narrating = false, paused = false, speed = 1, clock = 0, prevU = 0, focus = new Set();
  const CYCLE = 2.6; // 每個動作循環秒數（1.0x）

  function renderSubs(l) {
    let h = l.text; for (const w of [...l.hl].sort((a, b) => b.length - a.length)) h = h.split(w).join(`\u0000${w}\u0001`);
    $('subs').innerHTML = h.replace(/\u0000/g, '<mark>').replace(/\u0001/g, '</mark>');
  }
  function setFocus(keys) { focus = new Set(keys || []); $('compare').classList.toggle('hi', focus.has('compare')); $('stageWrap').classList.toggle('dimmed', focus.has('compare')); }
  function stopVoice() { voice.pause(); narrating = false; line = -1; sound.duck(false); setFocus([]); $('playBtn').textContent = '播放講解'; }
  function playLine(i) {
    const ch = chapters[cur];
    if (i >= ch.lines.length) { stopVoice(); $('subs').innerHTML = '講解完畢。可再看一次動畫，或往下看對照與影片。'; return; }
    line = i; const l = ch.lines[i];
    renderSubs(l); setFocus(l.focus);
    [...$('lineDots').children].forEach((d, k) => d.classList.toggle('on', k <= i));
    voice.src = manifest[`${ch.id}-${i + 1}`]; voice.currentTime = 0;
    voice.play().catch(() => setTimeout(() => playLine(i + 1), 2500));
  }
  voice.onended = () => { if (narrating) setTimeout(() => playLine(line + 1), 350); };
  voice.onerror = () => { if (narrating) setTimeout(() => playLine(line + 1), 1500); };

  function render(i) {
    stopVoice(); cur = i; const c = chapters[i];
    document.querySelectorAll('[data-chapter]').forEach((b, k) => b.classList.toggle('active', k === i));
    $('chapterTag').textContent = c.tag; $('chapterTitle').textContent = c.title; $('goal').textContent = c.goal;
    $('look').innerHTML = c.look.map((t, k) => `<li><b>${k + 1}</b>${t}</li>`).join('');
    const ph = c.photos || [];
    $('photoCard').hidden = ph.length === 0;
    $('photos').innerHTML = ph.map((p) => `<figure><img src="${p.src}" alt="${p.caption}" loading="lazy"><figcaption>${p.caption}</figcaption></figure>`).join('');
    $('wrong').textContent = c.wrong; $('fix').textContent = c.fix; $('question').textContent = c.question;
    $('lineDots').innerHTML = c.lines.map(() => '<i></i>').join('');
    $('subs').innerHTML = '按「播放講解」，旁白會一邊說明，一邊標示圖上要看的地方。';
    $('prev').disabled = i === 0; $('next').disabled = i === chapters.length - 1; $('count').textContent = `${i + 1} / ${chapters.length}`;
    $('videoSelect').value = String(c.video); clearVideo();
    history.replaceState(null, '', `#${i + 1}`);
  }
  function clearVideo() {
    $('publicFrame').removeAttribute('src'); $('publicFrame').hidden = true;
    const v = videos[+$('videoSelect').value]; $('videoSource').textContent = `${v.source}。播放前先看上方「看這裡」三個重點。`;
    $('externalVideo').href = `https://www.youtube.com/watch?v=${v.id}`;
  }

  $('photos').onclick = (e) => {
    const img = e.target.closest('img'); if (!img) return;
    const box = document.createElement('div'); box.id = 'lightbox';
    box.innerHTML = `<img src="${img.src}" alt="${img.alt}">`;
    box.onclick = () => box.remove();
    document.addEventListener('keydown', function esc(ev) { if (ev.key === 'Escape') { box.remove(); document.removeEventListener('keydown', esc); } });
    document.body.appendChild(box);
  };

  // UI
  $('chapters').innerHTML = chapters.map((c, i) => `<button data-chapter="${i}"><span>${c.tag}</span>${c.title}</button>`).join('');
  document.querySelectorAll('[data-chapter]').forEach((b) => (b.onclick = () => render(+b.dataset.chapter)));
  $('prev').onclick = () => render(Math.max(0, cur - 1)); $('next').onclick = () => render(Math.min(chapters.length - 1, cur + 1));
  $('playBtn').onclick = () => {
    sound.init();
    if (narrating) { stopVoice(); return; }
    narrating = true; paused = false; $('pauseBtn').textContent = '暫停動畫'; $('playBtn').textContent = '停止講解'; sound.duck(true); playLine(0);
  };
  $('pauseBtn').onclick = () => { paused = !paused; $('pauseBtn').textContent = paused ? '繼續動畫' : '暫停動畫'; };
  $('replayBtn').onclick = () => { sound.init(); clock = 0; prevU = 0; stopVoice(); narrating = true; $('playBtn').textContent = '停止講解'; sound.duck(true); playLine(0); };
  document.querySelectorAll('[data-speed]').forEach((b) => (b.onclick = () => {
    speed = +b.dataset.speed; document.querySelectorAll('[data-speed]').forEach((x) => x.classList.toggle('on', x === b));
  }));
  $('fxBtn').onclick = () => { sound.init(); sound.fx = !sound.fx; $('fxBtn').classList.toggle('on', sound.fx); $('fxBtn').textContent = sound.fx ? '動作音效：開' : '動作音效：關'; };
  $('bgmBtn').onclick = () => { sound.init(); sound.setBgm(!sound.bgmOn); $('bgmBtn').classList.toggle('on', sound.bgmOn); $('bgmBtn').textContent = sound.bgmOn ? '背景音樂：開' : '背景音樂：關'; };
  $('vol').oninput = (e) => { sound.vol = +e.target.value; voice.volume = Math.min(1, 0.4 + sound.vol); sound.applyBgm(); };
  $('videoSelect').innerHTML = videos.map((v, i) => `<option value="${i}">${v.title}</option>`).join('');
  $('videoSelect').onchange = clearVideo;
  $('loadPublic').onclick = () => { stopVoice(); const v = videos[+$('videoSelect').value]; $('publicFrame').src = `https://www.youtube-nocookie.com/embed/${v.id}`; $('publicFrame').hidden = false; };
  let videoURL = null;
  $('localFile').onchange = () => { const f = $('localFile').files[0]; if (!f) return; if (videoURL) URL.revokeObjectURL(videoURL); videoURL = URL.createObjectURL(f);
    $('ownVideo').src = videoURL; $('ownVideo').hidden = false; $('ownStatus').textContent = `已選取：${f.name}（只在本機播放，不會上傳）`; };
  $('localSpeed').onchange = () => { $('ownVideo').playbackRate = +$('localSpeed').value; };
  $('ownVideo').onloadedmetadata = () => { $('ownVideo').playbackRate = +$('localSpeed').value; };

  // 動畫迴圈
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (!paused) clock += dt * speed / CYCLE;
    const u = clock % 1, sc = SCENES[chapters[cur].scene];
    for (const e of sc.events || []) { const crossed = prevU <= u ? (prevU < e.u && u >= e.u) : (prevU < e.u || u >= e.u); if (crossed && !paused) sound.play(e.type); }
    prevU = u;
    $('stage').innerHTML = sc(u, { variant: 'good', focus });
    $('cmpGood').innerHTML = sc(u, { variant: 'good', mini: true });
    $('cmpBad').innerHTML = sc(u, { variant: 'bad', mini: true });
    $('phaseBar').style.width = `${u * 100}%`;
    requestAnimationFrame(frame);
  }
  const start = Math.max(1, Math.min(chapters.length, +(location.hash.slice(1)) || 1)) - 1;
  render(start);
  requestAnimationFrame(frame);
  window.__ready = true;
})().catch((e) => { document.body.insertAdjacentHTML('afterbegin', `<p style="color:#fca5a5;padding:1em">載入失敗：${e.message}（請用本機伺服器開啟）</p>`); console.error(e); });
