// ============================================================
// 羽球場 p5.js 動畫（網站版）
// 改編自使用者 P5js 作品：fluid3d/bg_light_art（光藝術對打）與 fluid3d/bg_mono_v2（線框球場）
// 用法：<section data-court="rally">（首頁）或 <section data-court="mono" data-hue="150">（分類目錄）
// - 首頁 rally：挑高球／放小球／殺球自動對打，擊球有光環、粒子、地面漣漪；點一下畫面 = 朝該處殺球
// - 目錄 mono：線框球場、羽球自動漂浮與殺球，拖尾顏色依分類
// 省電：畫面不在螢幕內或分頁在背景時暫停；系統設定「減少動態效果」時只畫一張靜態圖
// ============================================================
(function () {
  'use strict';
  if (typeof p5 === 'undefined') return;

  const K = 49, HW = 6.1 * K / 2, HL = 13.4 * K / 2, Y_FLOOR = 270, NET_H = 1.55 * K, G = 0.34;
  const SHUTTLE_S = 0.42;
  const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function isDark() {
    const r = document.documentElement;
    if (r.dataset.theme) return r.dataset.theme === 'dark';
    return window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // HSB 顏色表：淺色沿用原作，深色把線條改亮、地面改暗
  const PAL = {
    light: { floor: [42, 7, 93, 44], mat: [42, 4, 58, 42], line: [42, 5, 30], mesh: [42, 5, 48, 24], top: [42, 8, 24, 76], top2: [42, 4, 58, 52],
             bottom: [42, 4, 55, 35], post: [42, 8, 25, 86], base: [42, 5, 72, 44], ring: [42, 6, 37, 68], shadow: [42, 10, 26], rib: [42, 5, 34, 82],
             skirtRing: [42, 5, 52, 62], grid: [40, 4, 75, 9], pencil: [40, 5, 40], add: true },
    dark:  { floor: [160, 25, 16, 50], mat: [150, 10, 55, 40], line: [150, 8, 88], mesh: [150, 6, 80, 22], top: [0, 0, 96, 80], top2: [150, 6, 75, 45],
             bottom: [150, 6, 70, 30], post: [0, 0, 90, 85], base: [150, 10, 35, 50], ring: [150, 8, 75, 60], shadow: [0, 0, 0], rib: [0, 0, 70, 80],
             skirtRing: [0, 0, 80, 60], grid: [150, 8, 60, 10], pencil: [150, 10, 85], add: true }
  };

  function mount(el) {
    const mode = el.dataset.court === 'mono' ? 'mono' : 'rally';
    const hue = Number(el.dataset.hue || 172);
    const holder = document.createElement('div');
    holder.className = 'court-canvas';
    holder.setAttribute('aria-hidden', 'true');
    el.prepend(holder);

    new p5(function (s) {
      let shuttle = { pos: null, vel: null, mode: 'follow' };
      let shot = null, trail = [], ripples = [], bursts = [], sparks = [];
      let tGlobal = Math.random() * 10, camAz = 0, cameraPulse = 0, nextSmash = 300;
      const pointer = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };
      const PALETTE = [172, 200, 38, 350];
      let P = PAL.light;

      s.setup = function () {
        const r = holder.getBoundingClientRect();
        s.pixelDensity(Math.min(window.devicePixelRatio || 1, 2));   // 畫面變小，提高解析度保持細緻
        s.createCanvas(Math.max(1, r.width), Math.max(1, r.height), s.WEBGL).parent(holder);
        s.colorMode(s.HSB, 360, 100, 100, 100);
        s.frameRate(window.innerWidth < 700 ? 30 : 45);
        shuttle.pos = s.createVector(0, Y_FLOOR - NET_H - 80, HL * 0.7);
        shuttle.vel = s.createVector(0, 0, 0);
        if (mode === 'rally') serve();
        el.addEventListener('pointermove', onMove, { passive: true });
        if (mode === 'rally') el.addEventListener('pointerdown', onDown, { passive: true });
        new ResizeObserver(() => { const b = holder.getBoundingClientRect(); if (b.width > 0) s.resizeCanvas(b.width, b.height); if (reduceMotion) s.redraw(); }).observe(holder);
        // 不在畫面內／分頁在背景 → 暫停
        let onScreen = true;
        const sync = () => { if (!reduceMotion && onScreen && !document.hidden) s.loop(); else s.noLoop(); };
        new IntersectionObserver((es) => { onScreen = es[0].isIntersecting; sync(); }).observe(el);
        document.addEventListener('visibilitychange', sync);
        if (reduceMotion) { for (let i = 0; i < 60; i++) step(); s.noLoop(); }
        // 主題切換時重畫一次（暫停中也更新顏色）
        new MutationObserver(() => s.redraw()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
      };

      function step() {
        tGlobal += 0.004;
        if (mode === 'rally') { updateShot(); updateEffects(); } else updateFloat();
      }

      s.draw = function () {
        if (!reduceMotion) step();
        P = isDark() ? PAL.dark : PAL.light;
        pointer.x = s.lerp(pointer.x, pointer.tx, 0.08);
        pointer.y = s.lerp(pointer.y, pointer.ty, 0.08);
        cameraPulse *= 0.93;
        s.clear();
        const px = pointer.x - 0.5, py = pointer.y - 0.5;
        const aspect = s.width / Math.max(1, s.height);
        const fit = s.constrain(1.15 / aspect, 0.85, 1.45) * s.constrain(400 / Math.max(60, s.height), 1.3, 2.6);   // 畫面越矮，鏡頭越遠，整個球場都看得到
        const R = (mode === 'rally' ? 760 : 700) * fit - cameraPulse * 24;
        camAz = tGlobal * (mode === 'rally' ? 0.14 : 0.18) + px * 0.24 + Math.sin(tGlobal * 1.7) * 0.03;
        const elev = (mode === 'rally' ? 310 : 260) + Math.sin(tGlobal * 0.5) * 36 + py * 50 - cameraPulse * 16;
        s.camera(Math.sin(camAz) * R, Y_FLOOR - elev, Math.cos(camAz) * R, px * 60, Y_FLOOR - 15 + py * 14, 0, 0, 1, 0);         // 球場置中（文字已移到旁邊）
        if (mode === 'mono') drawGrid();
        drawCourt();
        drawShadow();
        if (mode === 'rally') { drawArcDots(); drawTrail(); drawRipples(); drawBursts(); } else drawPencilTrail();
        drawShuttle();
      };

      function onMove(e) {
        const b = el.getBoundingClientRect();
        pointer.tx = s.constrain((e.clientX - b.left) / Math.max(1, b.width), 0, 1);
        pointer.ty = s.constrain((e.clientY - b.top) / Math.max(1, b.height), 0, 1);
        if (reduceMotion) s.redraw();
      }
      function onDown(e) {
        if (e.target.closest('a,button,input,select,label')) return;
        onMove(e);
        const tx = s.map(pointer.tx, 0, 1, -HW * 0.8, HW * 0.8), tz = s.map(pointer.ty, 0, 1, -HL * 0.9, HL * 0.9);
        const from = shuttle.pos.copy();
        spawnBurst(from); spawnSparks(from, 14);
        const T = Math.floor(s.constrain(s.dist(from.x, from.z, tx, tz) / 13, 18, 34));
        launchShot(from, s.createVector(tx, Y_FLOOR - 8, tz), T, 'smash');
        cameraPulse = 1;
        if (reduceMotion) { for (let i = 0; i < T; i++) step(); s.redraw(); }
      }

      // ---------- 對打（rally） ----------
      function serve() {
        launchShot(s.createVector(s.random(-HW * 0.4, HW * 0.4), Y_FLOOR - 32, HL * 0.72),
          s.createVector(s.random(-HW * 0.5, HW * 0.5), Y_FLOOR - s.random(60, 100), -HL * s.random(0.55, 0.85)), Math.floor(s.random(78, 95)), 'clear');
      }
      function launchShot(p0, p1, T, type) {
        shot = { p0: p0.copy(), p1: p1.copy(), T, t: 0, type, vy0: (p1.y - p0.y) / T - 0.5 * G * T };
        shuttle.pos = p0.copy();
      }
      function shotPoint(u) {
        return s.createVector(s.lerp(shot.p0.x, shot.p1.x, u / shot.T), shot.p0.y + shot.vy0 * u + 0.5 * G * u * u, s.lerp(shot.p0.z, shot.p1.z, u / shot.T));
      }
      function updateShot() {
        if (!shot) return;
        shot.t++;
        shuttle.pos = shotPoint(shot.t);
        shuttle.vel = s.createVector((shot.p1.x - shot.p0.x) / shot.T, shot.vy0 + G * shot.t, (shot.p1.z - shot.p0.z) / shot.T);
        trail.push(shuttle.pos.copy()); if (trail.length > 64) trail.shift();
        if (shot.t >= shot.T) {
          const arr = shot.p1.copy();
          if (shot.type === 'smash') { spawnRipple(arr.x, arr.z, 1.35); spawnSparks(arr, 24); cameraPulse = Math.max(cameraPulse, 0.7); nextShotFrom(s.createVector(arr.x, Y_FLOOR - 20, arr.z), 'smash'); }
          else { spawnBurst(arr); spawnSparks(arr, 12); spawnRipple(arr.x, arr.z, 0.5); cameraPulse = Math.max(cameraPulse, 0.3); nextShotFrom(arr, shot.type); }
        }
      }
      function nextShotFrom(p, incoming) {
        const side = p.z >= 0 ? -1 : 1, r = s.random();
        let type, target, T;
        if (incoming === 'smash') { type = 'lift'; target = s.createVector(s.random(-HW * 0.6, HW * 0.6), Y_FLOOR - s.random(55, 95), side * s.random(HL * 0.55, HL * 0.85)); T = Math.floor(s.random(88, 106)); }
        else if (r < 0.22 && p.y < Y_FLOOR - NET_H - 26) { type = 'smash'; target = s.createVector(s.random(-HW * 0.55, HW * 0.55), Y_FLOOR - 8, side * s.random(HL * 0.3, HL * 0.7)); T = Math.floor(s.random(22, 30)); }
        else if (r < 0.48) { type = 'drop'; target = s.createVector(s.random(-HW * 0.6, HW * 0.6), Y_FLOOR - s.random(32, 55), side * s.random(K * 0.7, K * 1.9)); T = Math.floor(s.random(48, 62)); }
        else { type = 'clear'; target = s.createVector(s.random(-HW * 0.65, HW * 0.65), Y_FLOOR - s.random(55, 110), side * s.random(HL * 0.5, HL * 0.9)); T = Math.floor(s.random(74, 95)); }
        launchShot(p, target, T, type);
      }
      function spawnBurst(p) { bursts.push({ pos: p.copy(), age: 0, hue: s.random(PALETTE) }); if (bursts.length > 8) bursts.shift(); }
      function spawnRipple(x, z, power) { ripples.push({ x, z, age: 0, power }); if (ripples.length > 8) ripples.shift(); }
      function spawnSparks(p, n) {
        for (let i = 0; i < n; i++) { const a = s.random(s.TWO_PI), v = s.random(1.2, 4.2); sparks.push({ pos: p.copy(), vel: s.createVector(Math.cos(a) * v, s.random(-3.4, -0.8), Math.sin(a) * v), life: s.random(30, 58), hue: s.random(PALETTE) }); }
      }
      function updateEffects() {
        bursts.forEach(b => b.age++); bursts = bursts.filter(b => b.age < 46);
        ripples.forEach(r => r.age++); ripples = ripples.filter(r => r.age < 90);
        sparks.forEach(p => { p.vel.y += 0.08; p.vel.mult(0.985); p.pos.add(p.vel); p.life--; }); sparks = sparks.filter(p => p.life > 0);
      }
      function drawBursts() {
        s.push(); s.blendMode(s.ADD); s.noFill();
        for (const b of bursts) {
          const f = b.age / 46, e = 1 - Math.pow(1 - f, 3);
          s.push(); s.translate(b.pos.x, b.pos.y, b.pos.z); s.rotateY(camAz);
          s.stroke(b.hue, 36, 95, (1 - f) * 42); s.strokeWeight(2 - f); s.circle(0, 0, e * 84);
          s.stroke(42, 14, 98, (1 - f) * 22); s.circle(0, 0, e * 46); s.pop();
        }
        s.strokeWeight(3);
        for (const p of sparks) { s.stroke(p.hue, 38, 95, s.map(p.life, 0, 58, 0, 34, true)); s.point(p.pos.x, p.pos.y, p.pos.z); }
        s.blendMode(s.BLEND); s.pop();
      }
      function drawRipples() {
        s.push(); s.blendMode(s.ADD); s.noFill();
        for (const r of ripples) {
          const f = r.age / 90, e = 1 - Math.pow(1 - f, 3);
          s.push(); s.translate(r.x, Y_FLOOR - 1, r.z); s.rotateX(s.HALF_PI);
          s.stroke(184, 30, 94, (1 - f) * 32); s.strokeWeight(1.5); s.circle(0, 0, e * 140 * r.power);
          s.stroke(38, 26, 96, (1 - f) * 16); s.circle(0, 0, e * 82 * r.power); s.pop();
        }
        s.blendMode(s.BLEND); s.pop();
      }
      function drawArcDots() {
        if (!shot) return;
        s.push(); s.blendMode(s.ADD); s.strokeWeight(2.4);
        for (let u = shot.t; u <= shot.T; u += 4) { const p = shotPoint(u), near = 1 - (u - shot.t) / Math.max(1, shot.T); s.stroke(38, 30, 96, 6 + near * 10); s.point(p.x, p.y, p.z); }
        s.blendMode(s.BLEND); s.pop();
      }
      function drawTrail() {
        if (trail.length < 2) return;
        s.push(); s.blendMode(s.ADD); s.noFill();
        for (let i = 1; i < trail.length; i++) {
          const f = i / trail.length, a = trail[i - 1], b = trail[i];
          s.stroke(184, 24, 95, 18 * f * f); s.strokeWeight(4 * f); s.line(a.x, a.y, a.z, b.x, b.y, b.z);
          s.stroke(42, 8, 96, 30 * f * f); s.strokeWeight(1); s.line(a.x, a.y, a.z, b.x, b.y, b.z);
        }
        s.blendMode(s.BLEND); s.pop();
      }

      // ---------- 漂浮＋自動殺球（mono） ----------
      function updateFloat() {
        if (shuttle.mode === 'follow') {
          const tx = s.map(s.noise(tGlobal * 0.9), 0, 1, -HW, HW), tz = s.map(s.noise(tGlobal * 0.9 + 100), 0, 1, -HL, HL);
          const ty = Y_FLOOR - NET_H - 70 - Math.sin(tGlobal * 2) * 25;
          const steer = p5.Vector.sub(s.createVector(tx, ty, tz), shuttle.pos).mult(0.05);
          shuttle.vel.lerp(steer, 0.15); shuttle.pos.add(shuttle.vel);
          if (--nextSmash <= 0) { shuttle.vel = s.createVector(s.random(-2, 2), -5, (shuttle.pos.z > 0 ? -1 : 1) * 24); shuttle.mode = 'smash'; nextSmash = Math.floor(s.random(300, 540)); }
        } else {
          shuttle.vel.y += 0.35; shuttle.vel.add(shuttle.vel.copy().mult(-0.0072 * shuttle.vel.mag())); shuttle.pos.add(shuttle.vel);
          if (shuttle.pos.y >= Y_FLOOR - 6) { shuttle.pos.y = Y_FLOOR - 6; shuttle.mode = 'follow'; shuttle.vel.mult(0); }
        }
        trail.push(shuttle.pos.copy()); if (trail.length > 70) trail.shift();
      }
      function drawPencilTrail() {
        if (trail.length < 2) return;
        s.push(); s.noFill();
        for (let i = 1; i < trail.length; i++) {
          const f = i / trail.length, a = trail[i - 1], b = trail[i];
          s.stroke(hue, 55, isDark() ? 90 : 60, 55 * f * f); s.strokeWeight(1 + f * 1.5); s.line(a.x, a.y, a.z, b.x, b.y, b.z);
        }
        s.pop();
      }
      function drawGrid() {
        s.push(); s.stroke(...P.grid); s.strokeWeight(0.6);
        const EXT = 10 * K;
        for (let g = -EXT; g <= EXT; g += K) { s.line(g, Y_FLOOR + 0.5, -EXT, g, Y_FLOOR + 0.5, EXT); s.line(-EXT, Y_FLOOR + 0.5, g, EXT, Y_FLOOR + 0.5, g); }
        s.pop();
      }

      // ---------- 球場、球網、羽球 ----------
      function drawCourt() {
        const y = Y_FLOOR;
        s.push();
        if (mode === 'rally') {
          s.noStroke(); s.fill(...P.floor);
          s.beginShape(); s.vertex(-HW - 30, y + 0.6, -HL - 30); s.vertex(HW + 30, y + 0.6, -HL - 30); s.vertex(HW + 30, y + 0.6, HL + 30); s.vertex(-HW - 30, y + 0.6, HL + 30); s.endShape(s.CLOSE);
        }
        s.noFill(); s.stroke(...P.mat); s.strokeWeight(1);
        s.beginShape(); s.vertex(-HW - 30, y, -HL - 30); s.vertex(HW + 30, y, -HL - 30); s.vertex(HW + 30, y, HL + 30); s.vertex(-HW - 30, y, HL + 30); s.endShape(s.CLOSE);
        const breathe = 0.5 + 0.5 * Math.sin(tGlobal * 9.5);
        s.strokeWeight(1.45 + breathe * 0.45);
        const L = (x1, z1, x2, z2, ph) => { s.stroke(P.line[0], P.line[1], P.line[2], 54 + 20 * s.noise(ph, tGlobal * 3.8)); s.line(x1, y, z1, x2, y, z2); };
        L(-HW, -HL, HW, -HL, 1); L(-HW, HL, HW, HL, 2); L(-HW, -HL, -HW, HL, 3); L(HW, -HL, HW, HL, 4);
        const sw = HW - 0.46 * K; L(-sw, -HL, -sw, HL, 5); L(sw, -HL, sw, HL, 6);
        const ss = 1.98 * K; L(-HW, -ss, HW, -ss, 7); L(-HW, ss, HW, ss, 8);
        const dl = HL - 0.76 * K; L(-HW, -dl, HW, -dl, 9); L(-HW, dl, HW, dl, 10);
        L(0, -HL, 0, -ss, 11); L(0, ss, 0, HL, 12);
        drawNet(y);
        s.pop();
      }
      function drawNet(y) {
        const NET_D = 0.76 * K, SAG = 3, yTop = x => y - NET_H + SAG * (1 - (x / HW) ** 2), xAt = (i, n) => s.lerp(-HW, HW, i / n);
        const NV = Math.round(2 * HW / 9), NH = 26;
        s.push();
        s.stroke(...P.mesh); s.strokeWeight(0.6);
        for (let i = 0; i <= NV; i++) { const x = xAt(i, NV); s.line(x, yTop(x), 0, x, yTop(x) + NET_D, 0); }
        for (let d = 6; d <= NET_D; d += 9) { s.beginShape(); for (let i = 0; i <= NH; i++) { const x = xAt(i, NH); s.vertex(x, yTop(x) + d, 0); } s.endShape(); }
        const band = (c, w, dy) => { s.stroke(...c); s.strokeWeight(w); s.beginShape(); for (let i = 0; i <= NH; i++) { const x = xAt(i, NH); s.vertex(x, yTop(x) + dy, 0); } s.endShape(); };
        band(P.top, 2.2, 0); band(P.top2, 1, 4); band(P.bottom, 1, NET_D);
        for (const px of [-HW - 3, HW + 3]) {
          s.stroke(...P.post); s.strokeWeight(2.6); s.line(px, y - NET_H, 0, px, y - 6, 0); s.strokeWeight(4); s.point(px, y - NET_H, 0);
          s.noStroke(); s.fill(...P.base); s.push(); s.translate(px, y - 1, 0); s.rotateX(s.HALF_PI); s.circle(0, 0, 36); s.pop();
          s.noFill(); s.stroke(...P.ring); s.strokeWeight(1.2); s.push(); s.translate(px, y - 1.5, 0); s.rotateX(s.HALF_PI); s.circle(0, 0, 36); s.circle(0, 0, 16); s.pop();
        }
        s.pop();
      }
      function drawShadow() {
        const h = Y_FLOOR - shuttle.pos.y;
        s.push(); s.translate(shuttle.pos.x, Y_FLOOR - 0.5, shuttle.pos.z); s.rotateX(s.HALF_PI); s.noStroke();
        s.fill(P.shadow[0], P.shadow[1], P.shadow[2], s.map(h, 0, 300, isDark() ? 40 : 24, 5, true)); s.circle(0, 0, s.map(h, 0, 300, 9, 24, true) * 2); s.pop();
      }
      function drawShuttle() {
        const CR = 7, SR = 18, FL = 30;
        s.push(); s.translate(shuttle.pos.x, shuttle.pos.y, shuttle.pos.z);
        let dir = shuttle.vel.copy(); if (dir.mag() < 0.5) dir = s.createVector(0, 1, 0); dir.normalize();
        s.rotateY(Math.atan2(dir.x, dir.z)); s.rotateX(-Math.asin(s.constrain(dir.y, -1, 1))); s.rotateX(s.HALF_PI); s.scale(SHUTTLE_S);
        s.noStroke(); s.fill(0, 0, 100);
        s.push(); s.translate(0, -16, 0); s.sphere(CR, 16, 12); s.pop();
        s.push(); s.translate(0, -10, 0); s.cylinder(CR, 12, 16, 4); s.pop();
        s.fill(42, 5, 88); s.push(); s.translate(0, -4, 0); s.cylinder(CR + 0.6, 3.5, 16, 2); s.pop();
        s.fill(0, 0, 100, 28); s.beginShape(s.TRIANGLE_STRIP);
        for (let a = 0; a <= s.TWO_PI + 0.01; a += s.TWO_PI / 24) { s.vertex(Math.cos(a) * (CR + 0.5), -2, Math.sin(a) * (CR + 0.5)); s.vertex(Math.cos(a) * SR, -2 + FL, Math.sin(a) * SR); }
        s.endShape();
        s.stroke(...P.rib); s.strokeWeight(1);
        for (let i = 0; i < 16; i++) { const a = i * s.TWO_PI / 16; s.line(Math.cos(a) * (CR + 0.5), -2, Math.sin(a) * (CR + 0.5), Math.cos(a) * (SR + 1.5), FL, Math.sin(a) * (SR + 1.5)); }
        s.noFill(); s.stroke(...P.skirtRing); s.strokeWeight(0.8);
        for (const ry of [FL - 10, FL - 3]) { const rr = s.map(ry, -2, FL - 2, CR + 0.5, SR); s.beginShape(); for (let a = 0; a <= s.TWO_PI + 0.01; a += s.TWO_PI / 24) s.vertex(Math.cos(a) * rr, ry, Math.sin(a) * rr); s.endShape(); }
        s.pop();
      }
    });
  }

  function start() {
    let gl = null;
    try { gl = document.createElement('canvas').getContext('webgl'); } catch (e) { gl = null; }
    if (!gl) return;                       // 沒有 WebGL：保留 CSS 漸層底，不顯示動畫
    document.querySelectorAll('[data-court]').forEach(el => { try { mount(el); } catch (e) { /* 動畫失敗不影響內容 */ } });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
