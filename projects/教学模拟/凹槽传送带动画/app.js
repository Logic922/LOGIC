(function () {
'use strict';

/* =====================================================================
   物理模型
   ---------------------------------------------------------------------
   t = 0 为 A 右端与 C 接触（弹性碰撞）的瞬间。
   碰撞后：v_A = -5（左），v_C = +5（右），v_B 仍为 +10。
   此后 A+B 组成的系统只受内力（B 与 A 的摩擦），质心速度恒定：
       v_cm = (2·(-5) + 0.5·10)/2.5 = -2 m/s
   相对运动只由一个量 u = v_B - v_A 决定：
       v_B = v_cm + (m_A/M)·u = -2 + 0.8u
       v_A = v_cm - (m_B/M)·u = -2 - 0.2u
   滑动时 |u| 以 a_rel = μ₁g(1+m_B/m_A) = 2.5 m/s² 匀速减小；
   B 撞挡板是弹性碰撞 ⇒ u 只反向，大小不变。
   记 s 为 B 距 A 左端的距离，则 ds/dt = u，
   A 右端的世界坐标  x_A = x₀ - 2t - 0.2·s(t)。
   ===================================================================== */

var G = 10, mA = 2, mB = 0.5, mC = 6;
var L = 8, V0 = 10, MU1 = 0.2, MU2 = 0.5;
var VCM = -2;                       // 质心速度（碰 C 之后恒定）
var AREL = MU1 * G * (1 + mB / mA); // 2.5
var BELT_V = -2;                    // 带面速度（向左）
var C_W = 0.9, C_H = 0.7;           // C 的视觉尺寸
var BELT_X0 = 2.05, BELT_X1 = 5.45; // 传送带左/右端（世界坐标）
var X0 = -0.45;                     // t=0 时 A 右端外表面的世界坐标

/* ---- 把 B 在 A 内的运动拆成解析段 ---- */
var segs = [], hits = [], T_STOP = 0;
(function build() {
  var t = 0, s = 0, u = V0 - (-5), guard = 0; // u 初值 = 15
  while (Math.abs(u) > 1e-9 && guard++ < 40) {
    var tgt = u > 0 ? L : 0;
    var au = -Math.sign(u) * AREL;
    var u2 = u * u + 2 * au * (tgt - s);
    if (u2 <= 1e-9) {                       // 到不了挡板，先相对静止
      var dt0 = Math.abs(u) / AREL;
      var dss = -u * u / (2 * au);
      segs.push({ t0: t, t1: t + dt0, s0: s, s1: s + dss, u0: u, u1: 0, au: au });
      t += dt0; s += dss; u = 0;
      break;
    }
    var uf = Math.sign(u) * Math.sqrt(u2);
    var dt = (Math.abs(u) - Math.abs(uf)) / AREL;
    segs.push({ t0: t, t1: t + dt, s0: s, s1: tgt, u0: u, u1: uf, au: au });
    t += dt; s = tgt;
    hits.push({ t: t, side: u > 0 ? 'R' : 'L', n: hits.length + 1 });
    u = -uf;                                 // 弹性碰撞：相对速度反向
  }
  T_STOP = t;
})();

function bState(t) {
  if (t <= 0) return { s: 0, u: 0, vA: V0, vB: V0 };
  var seg = segs[segs.length - 1];
  for (var i = 0; i < segs.length; i++) {
    if (t < segs[i].t1 - 1e-12) { seg = segs[i]; break; }
  }
  var tau = t - seg.t0;
  if (tau < 0) tau = 0;
  var dur = seg.t1 - seg.t0;
  if (tau > dur) tau = dur;
  var u = seg.u0 + seg.au * tau;
  var s = seg.s0 + seg.u0 * tau + 0.5 * seg.au * tau * tau;
  if (s < 0) s = 0; else if (s > L) s = L;
  return {
    s: s, u: u,
    vA: VCM - 0.2 * u,
    vB: VCM + 0.8 * u
  };
}

/* A 右端外表面的世界坐标 */
function xAR(t) {
  if (t <= 0) return X0 + V0 * t;
  return X0 - 2 * t - 0.2 * bState(t).s;
}

/* C 的质心位置与速度（t=0 时在 x=0 静止，随后被撞出） */
function cState(t) {
  if (t <= 0) return { x: 0, v: 0 };
  if (t <= 0.5) return { x: 5 * t, v: 5 };                      // 地面滑行 5 m/s
  if (t <= 1.5) { var a = t - 0.5; return { x: 2.5 + 5 * a - 2.5 * a * a, v: 5 - 5 * a }; } // 带上减速 a=-5
  if (t <= 1.9) { var b = t - 1.5; return { x: 5 - 2.5 * b * b, v: -5 * b }; }               // 反向加速
  return { x: 4.6 - 2 * (t - 1.9), v: -2 };                     // 与带共速向左
}

/* 关键时刻 */
var T_END = 8.2, T_BEG = -0.9;

/* =====================================================================
   绘图工具
   ===================================================================== */
var cvA = document.getElementById('cvA');
var cvC = document.getElementById('cvC');
var cvO = document.getElementById('cvO');
var cvT = document.getElementById('cvT');

function fit(cv) {
  var dpr = Math.min(window.devicePixelRatio || 1, 2.5);
  var r = cv.getBoundingClientRect();
  var w = Math.max(1, Math.round(r.width * dpr));
  var h = Math.max(1, Math.round(r.height * dpr));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  var ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx: ctx, W: r.width, H: r.height };
}

function rr(ctx, x, y, w, h, r) {
  if (w < 0) { x += w; w = -w; }
  if (h < 0) { y += h; h = -h; }
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function arrow(ctx, x1, y1, x2, y2, color, lw) {
  var dx = x2 - x1, dy = y2 - y1;
  var len = Math.hypot(dx, dy);
  if (len < 1.2) return;
  var ux = dx / len, uy = dy / len;
  var head = Math.min(9, len * 0.42);
  ctx.save();
  ctx.strokeStyle = color; ctx.fillStyle = color;
  ctx.lineWidth = lw || 2; ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x1, y1); ctx.lineTo(x2 - ux * head * 0.8, y2 - uy * head * 0.8);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - ux * head - uy * head * 0.44, y2 - uy * head + ux * head * 0.44);
  ctx.lineTo(x2 - ux * head + uy * head * 0.44, y2 - uy * head - ux * head * 0.44);
  ctx.closePath(); ctx.fill();
  ctx.restore();
}

function label(ctx, txt, x, y, color, align, size) {
  ctx.save();
  ctx.font = '600 ' + (size || 11) + 'px "PingFang SC","Noto Sans CJK SC",-apple-system,sans-serif';
  ctx.textAlign = align || 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = color;
  ctx.fillText(txt, x, y);
  ctx.restore();
}

/* 地面：底色 + 随镜头移动的斜纹 */
function drawGround(ctx, W, H, gY, camPx, step) {
  var g = ctx.createLinearGradient(0, gY, 0, H);
  g.addColorStop(0, '#0b1220');
  g.addColorStop(1, '#05080d');
  ctx.fillStyle = g;
  ctx.fillRect(0, gY, W, H - gY);

  ctx.save();
  ctx.beginPath(); ctx.rect(0, gY, W, H - gY); ctx.clip();
  ctx.strokeStyle = 'rgba(96,132,180,0.15)';
  ctx.lineWidth = 1;
  var sp = step || 17;
  var off = ((camPx % sp) + sp) % sp;
  for (var x = -H - sp; x < W + H; x += sp) {
    ctx.beginPath();
    ctx.moveTo(x + off, H);
    ctx.lineTo(x + off + (H - gY), gY);
    ctx.stroke();
  }
  ctx.restore();

  var lg = ctx.createLinearGradient(0, 0, W, 0);
  lg.addColorStop(0, 'rgba(120,175,230,0.15)');
  lg.addColorStop(0.5, 'rgba(140,195,255,0.75)');
  lg.addColorStop(1, 'rgba(120,175,230,0.15)');
  ctx.strokeStyle = lg; ctx.lineWidth = 1.4;
  ctx.beginPath(); ctx.moveTo(0, gY + 0.5); ctx.lineTo(W, gY + 0.5); ctx.stroke();
}

/* 传送带（含地下滚筒），地面 y=0 处与地面齐平 */
function drawBelt(ctx, X, Y, S, t) {
  var x0 = X(BELT_X0), x1 = X(BELT_X1);
  var yTop = Y(0), yBot = Y(-0.62);
  var rad = 0.3 * S;

  // 槽
  ctx.fillStyle = '#05080e';
  rr(ctx, x0 - rad - 2, yTop, (x1 - x0) + (rad + 2) * 2, yBot - yTop, 3);
  ctx.fill();

  // 带面（上表面）
  var grd = ctx.createLinearGradient(0, yTop - 2, 0, yTop + 7);
  grd.addColorStop(0, '#37485e');
  grd.addColorStop(1, '#1d2836');
  ctx.fillStyle = grd;
  ctx.fillRect(x0, yTop - 1.5, x1 - x0, 5);

  // 流动条纹
  ctx.save();
  ctx.beginPath(); ctx.rect(x0, yTop - 1.5, x1 - x0, 5); ctx.clip();
  ctx.strokeStyle = 'rgba(120,200,255,0.55)';
  ctx.lineWidth = 2;
  var sp = 16;
  var off = (((BELT_V * t * S) % sp) + sp) % sp;
  for (var x = x0 - sp; x < x1 + sp; x += sp) {
    ctx.beginPath();
    ctx.moveTo(x + off, yTop + 3.5);
    ctx.lineTo(x + off + 4, yTop - 1.5);
    ctx.stroke();
  }
  ctx.restore();

  // 滚筒
  [x0 + rad * 0.92, x1 - rad * 0.92].forEach(function (cx) {
    var cy = yTop + rad;
    ctx.beginPath(); ctx.arc(cx, cy, rad, 0, Math.PI * 2);
    ctx.fillStyle = '#131c28'; ctx.fill();
    ctx.strokeStyle = '#33465e'; ctx.lineWidth = 2; ctx.stroke();
    // 辐条
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-BELT_V * t / rad * 0.55);
    ctx.strokeStyle = '#2b3a4e'; ctx.lineWidth = 1.6;
    for (var k = 0; k < 3; k++) {
      var a = k * Math.PI / 3;
      ctx.beginPath();
      ctx.moveTo(-Math.cos(a) * rad * 0.78, -Math.sin(a) * rad * 0.78);
      ctx.lineTo(Math.cos(a) * rad * 0.78, Math.sin(a) * rad * 0.78);
      ctx.stroke();
    }
    ctx.restore();
    ctx.beginPath(); ctx.arc(cx, cy, rad * 0.16, 0, Math.PI * 2);
    ctx.fillStyle = '#3d5371'; ctx.fill();
  });

  // 带速箭头（画在滚筒之间的槽内，避免与 C 重叠）
  var ay = Y(-0.40);
  arrow(ctx, X(BELT_X1 - 0.62), ay, X(BELT_X0 + 0.62), ay, 'rgba(120,200,255,0.9)', 1.7);
  label(ctx, '带速 2 m/s', (x0 + x1) / 2, ay + 11, 'rgba(120,200,255,0.75)', 'center', 9.5);
}

/* 凹槽 A */
function drawAObj(ctx, X, Y, S, xr, t, flash) {
  var xl = xr - L;
  var wThk = 0.30;        // 底板厚
  var wall = 0.28;        // 挡板厚
  var wallH = 1.15;

  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.55)';
  ctx.shadowBlur = 12 * (S / 50);
  ctx.shadowOffsetY = 3;

  var g = ctx.createLinearGradient(0, Y(wallH), 0, Y(0));
  g.addColorStop(0, '#54789c');
  g.addColorStop(0.45, '#3a5674');
  g.addColorStop(1, '#24374c');
  ctx.fillStyle = g;

  // 底板（横跨整个凹槽）
  rr(ctx, X(xl - wall), Y(wThk), (L + wall * 2) * S, wThk * S, 2);
  ctx.fill();

  // 两侧挡板
  rr(ctx, X(xl - wall), Y(wallH), wall * S, wallH * S, 2);
  ctx.fill();
  rr(ctx, X(xr), Y(wallH), wall * S, wallH * S, 2);
  ctx.fill();
  ctx.restore();

  // 被撞的挡板发亮
  if (flash && flash.p > 0.02) {
    var hitX = flash.side === 'R' ? xr : xl - wall;
    ctx.save();
    ctx.globalAlpha = 0.55 + 0.45 * flash.p;
    ctx.fillStyle = '#ffe6a8';
    rr(ctx, X(hitX), Y(wallH), wall * S, wallH * S, 2);
    ctx.fill();
    ctx.restore();
  }

  // 内表面高光
  ctx.strokeStyle = 'rgba(150,200,255,0.45)';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(X(xl), Y(wallH)); ctx.lineTo(X(xl), Y(wThk));
  ctx.lineTo(X(xr), Y(wThk));
  ctx.lineTo(X(xr), Y(wallH));
  ctx.stroke();

  // 底板顶面亮度
  ctx.strokeStyle = 'rgba(140,190,240,0.28)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(X(xl), Y(wThk)); ctx.lineTo(X(xr), Y(wThk));
  ctx.stroke();

  // A 的标签
  label(ctx, 'A', X((xl + xr) / 2), Y(wThk) + 15, 'rgba(150,190,235,0.55)', 'center', 13);

  // 碰撞闪光
  if (flash && flash.p > 0.01) {
    var fx = flash.side === 'R' ? X(xr) : X(xl);
    var fy = Y(0.62);
    var R = (10 + 16 * (1 - flash.p)) * (S / 50);
    var rg = ctx.createRadialGradient(fx, fy, 0, fx, fy, R);
    rg.addColorStop(0, 'rgba(255,240,170,' + (0.85 * flash.p) + ')');
    rg.addColorStop(1, 'rgba(255,200,80,0)');
    ctx.fillStyle = rg;
    ctx.beginPath(); ctx.arc(fx, fy, R, 0, Math.PI * 2); ctx.fill();

    ctx.save();
    ctx.globalAlpha = flash.p;
    ctx.shadowColor = 'rgba(0,0,0,0.95)'; ctx.shadowBlur = 5;
    label(ctx, '✳ 第 ' + flash.n + ' 次碰撞', fx, Y(-0.42), '#ffd875', 'center', 10.5);
    ctx.restore();
  }
  return { xl: xl };
}

/* 方块 C */
function drawCObj(ctx, X, Y, S, c, t, glow) {
  var w = C_W * S, h = C_H * S;
  var x = X(c.x - C_W / 2), y = Y(C_H);
  ctx.save();
  if (glow) {
    ctx.shadowColor = 'rgba(45,212,191,0.7)';
    ctx.shadowBlur = 16 * (S / 60);
  }
  var g = ctx.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0, '#45e3cf');
  g.addColorStop(1, '#177e75');
  ctx.fillStyle = g;
  rr(ctx, x, y, w, h, Math.max(2, 0.07 * S));
  ctx.fill();
  ctx.restore();
  ctx.strokeStyle = 'rgba(160,255,245,0.6)';
  ctx.lineWidth = 1.2;
  rr(ctx, x, y, w, h, Math.max(2, 0.07 * S));
  ctx.stroke();
  label(ctx, 'C', x + w / 2, y + h / 2, 'rgba(4,40,38,0.85)', 'center', Math.min(15, h * 0.4));
}

/* =====================================================================
   场景 ①：凹槽 A 与滑块 B（镜头跟随）
   ===================================================================== */
var VIEW_A = 10.8;

function getFlash(t) {
  var best = null;
  for (var i = 0; i < hits.length; i++) {
    var d = Math.abs(t - hits[i].t);
    if (d < 0.14) {
      var p = 1 - d / 0.14;
      if (!best || p > best.p) best = { p: p, side: hits[i].side, n: hits[i].n };
    }
  }
  return best;
}

function drawSceneA(t) {
  var f = fit(cvA), ctx = f.ctx, W = f.W, H = f.H;
  var st = bState(t);
  var xr = xAR(t), xl = xr - L;
  var off = 0.9;                  // A 略偏左，右侧留出空间显示 C
  var cam = xr - L / 2 + off;
  var S = W / VIEW_A;
  var gY = H * 0.80;
  var X = function (x) { return (x - cam) * S + W / 2; };
  var Y = function (y) { return gY - y * S; };

  var bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#0d1420'); bg.addColorStop(0.62, '#080c13'); bg.addColorStop(1, '#05070b');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  // 淡网格（增加景深感）
  ctx.save();
  ctx.strokeStyle = 'rgba(80,120,170,0.045)';
  ctx.lineWidth = 1;
  var gs = 1 * S;
  var gx = ((X(0) % gs) + gs) % gs;
  for (var x = gx; x < W; x += gs) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, gY); ctx.stroke(); }
  for (var y = gY; y > 0; y -= gs) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  ctx.restore();

  drawGround(ctx, W, H, gY, cam * S, 17);

  // 传送带与 C（若在视野内）
  if (X(BELT_X0) < W + 200 && X(BELT_X1) > -200) drawBelt(ctx, X, Y, S, t);
  var c = cState(t);
  if (X(c.x) > -120 && X(c.x) < W + 120) {
    drawCObj(ctx, X, Y, S, c, t, Math.abs(c.v) > 0.1);
  }

  // A
  var flash = getFlash(t);
  var ao = drawAObj(ctx, X, Y, S, xr, t, flash);

  // B：球
  var r = 0.2 * S;
  var bx = X(xl + st.s), by = Y(0.22 + 0.2);
  var bg2 = ctx.createRadialGradient(bx - r * 0.35, by - r * 0.4, r * 0.1, bx, by, r);
  bg2.addColorStop(0, '#ffe08a');
  bg2.addColorStop(0.55, '#f5a524');
  bg2.addColorStop(1, '#b46a06');
  ctx.save();
  ctx.shadowColor = 'rgba(245,165,36,0.4)';
  ctx.shadowBlur = 5 * (S / 50);
  ctx.beginPath(); ctx.arc(bx, by, r, 0, Math.PI * 2);
  ctx.fillStyle = bg2; ctx.fill();
  ctx.restore();
  ctx.beginPath();
  ctx.arc(bx, by, r, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(255,225,150,0.65)'; ctx.lineWidth = 1.2; ctx.stroke();
  label(ctx, 'B', bx, by + 1, 'rgba(70,35,0,0.9)', 'center', Math.max(8, r * 0.9));

  // ---- 速度箭头 ----
  var k = 0.085;            // m/s -> m
  var yA = Y(1.62);
  if (Math.abs(st.vA) > 0.05) {
    var ax2 = X(xr - L / 2) + (st.vA > 0 ? 1 : -1) * 0;
    arrow(ctx, X(xr - L / 2), yA, X(xr - L / 2) + st.vA * k * S, yA,
      st.vA > 0 ? '#7fc4f5' : '#9fb4cc', 2.2);
    label(ctx, 'vA ' + Math.abs(st.vA).toFixed(2), X(xr - L / 2) + st.vA * k * S / 2, yA - 10, '#8fb8dd', 'center', 10.5);
  }

  var yB = Y(1.06);
  if (Math.abs(st.vB) > 0.05) {
    arrow(ctx, bx, yB, bx + st.vB * k * S, yB, '#f5b942', 2.2);
    label(ctx, 'vB ' + Math.abs(st.vB).toFixed(2), bx + st.vB * k * S / 2, yB - 10, '#e9b45c', 'center', 10.5);
  }

  // ---- 相对速度条 ----
  if (Math.abs(st.u) > 0.05) {
    var ux = W - 16, uy = 44;
    ctx.save();
    ctx.font = '600 10.5px "PingFang SC",-apple-system,sans-serif';
    ctx.textAlign = 'right';
    ctx.fillStyle = '#8c9db3';
    ctx.fillText('B 相对 A', ux, uy - 14);
    ctx.fillStyle = st.u > 0 ? '#f5a524' : '#57a8e0';
    ctx.fillText((st.u > 0 ? '→ ' : '← ') + Math.abs(st.u).toFixed(1) + ' m/s', ux, uy);
    ctx.restore();
  }

  // ---- 静止后标注 d ----
  if (t > T_STOP) {
    var yy = Y(0.2) - 6;
    var x1p = X(xl + st.s), x2p = X(xr);
    ctx.save();
    ctx.setLineDash([3, 3]);
    ctx.strokeStyle = 'rgba(120,220,200,0.85)'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(x1p, Y(0.2) + 2); ctx.lineTo(x1p, yy - 20); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2p, Y(0.2) + 2); ctx.lineTo(x2p, yy - 20); ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(x1p, yy - 12); ctx.lineTo(x2p, yy - 12); ctx.stroke();
    // 端点短竖线
    ctx.beginPath(); ctx.moveTo(x1p, yy - 17); ctx.lineTo(x1p, yy - 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2p, yy - 17); ctx.lineTo(x2p, yy - 7); ctx.stroke();
    ctx.restore();
    label(ctx, 'd = ' + (L - st.s).toFixed(2) + ' m', (x1p + x2p) / 2, yy - 22, '#7fe0cb', 'center', 11);
  }

  // ---- 左上角 HUD ----
  ctx.save();
  ctx.font = '600 10.5px "PingFang SC",-apple-system,sans-serif';
  ctx.textAlign = 'left'; ctx.fillStyle = '#7f93ab';
  ctx.fillText('碰撞次数  ' + countHits(t), 12, 18);
  ctx.fillText('相对速度  ' + Math.abs(st.u).toFixed(2) + ' m/s', 12, 33);
  ctx.restore();
}

function countHits(t) {
  var n = 0;
  for (var i = 0; i < hits.length; i++) if (t >= hits[i].t - 1e-9) n++;
  return n;
}

/* =====================================================================
   场景 ②：传送带上的 C（固定镜头）
   ===================================================================== */
var VIEW_C = 6.6, CAM_C = 2.72;

function drawSceneC(t) {
  var f = fit(cvC), ctx = f.ctx, W = f.W, H = f.H;
  var S = W / VIEW_C;
  var gY = H * 0.63;
  var X = function (x) { return (x - CAM_C) * S + W / 2; };
  var Y = function (y) { return gY - y * S; };

  var bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#0d1420'); bg.addColorStop(1, '#05070b');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  // 地面
  ctx.save();
  ctx.strokeStyle = 'rgba(80,120,170,0.05)'; ctx.lineWidth = 1;
  var gs = 1 * S;
  for (var x = 0; x < W; x += gs) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, gY); ctx.stroke(); }
  ctx.restore();

  drawGround(ctx, W, H, gY, 0, 17);
  drawBelt(ctx, X, Y, S, t);

  var c = cState(t);
  drawCObj(ctx, X, Y, S, c, t, Math.abs(c.v) > 0.1);

  // 速度箭头
  var k = 0.30;
  var ay = Y(C_H + 0.22);
  if (Math.abs(c.v) > 0.04) {
    var ax0 = X(c.x), ax1 = ax0 + c.v * k * S;
    arrow(ctx, ax0, ay, ax1, ay, c.v > 0 ? '#5ee0cd' : '#7fc4f5', 2.4);
    label(ctx, Math.abs(c.v).toFixed(2) + ' m/s', (ax0 + ax1) / 2, ay - 11, '#8ee8db', 'center', 11);
  } else if (Math.abs(t - 1.5) < 0.25) {
    label(ctx, 'v = 0 · 恰好到达右端', X(c.x), ay - 11, '#ffd875', 'center', 11);
  }

  // 右端端点标记
  ctx.save();
  ctx.strokeStyle = 'rgba(120,200,255,0.35)';
  ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(X(BELT_X1), Y(0)); ctx.lineTo(X(BELT_X1), Y(1.05)); ctx.stroke();
  ctx.restore();

  // 状态角标
  ctx.save();
  ctx.font = '600 10.5px "PingFang SC",-apple-system,sans-serif';
  ctx.textAlign = 'left'; ctx.fillStyle = '#7f93ab';
  var tag = 'C 在带上';
  if (t < 0) tag = 'C 静止';
  else if (t < 0.5) tag = 'C 在地面上滑行';
  else if (t <= 1.5) tag = '带上减速（a = −5 m/s²）';
  else if (t < 1.9) tag = '反向加速（仍在带上）';
  else if (c.x > BELT_X0) tag = '与带共速，随带向左';
  else tag = '离开传送带';
  ctx.fillText(tag, 12, 18);
  if (t > 3.0) {
    ctx.fillStyle = 'rgba(140,200,255,0.55)';
    ctx.fillText(t > 6.2 ? 'C 以 2 m/s 向左匀速，与 A、B 同速，永不追尾' : 'C 已随带子向左离开（2 m/s 匀速）', 12, 34);
  }
  ctx.restore();
  ctx.save();
  ctx.font = '10px "PingFang SC",-apple-system,sans-serif';
  ctx.textAlign = 'left';
  ctx.fillStyle = 'rgba(120,200,255,0.45)';
  ctx.fillText('带上减速 2.5 m 后速度恰为 0', 12, H - 8);
  ctx.restore();
}

/* =====================================================================
   全景
   ===================================================================== */
var OV_X0 = -26.5, OV_X1 = 6.6;

function drawOverview(t) {
  var f = fit(cvO), ctx = f.ctx, W = f.W, H = f.H;
  var S = W / (OV_X1 - OV_X0);
  var gY = H - 22;
  var X = function (x) { return (x - OV_X0) * S; };

  ctx.clearRect(0, 0, W, H);

  // 地面
  ctx.strokeStyle = 'rgba(110,150,200,0.35)';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, gY + 0.5); ctx.lineTo(W, gY + 0.5); ctx.stroke();

  // 传送带
  ctx.fillStyle = 'rgba(90,180,235,0.35)';
  ctx.fillRect(X(BELT_X0), gY, (BELT_X1 - BELT_X0) * S, 4);

  // 主视图视野框
  var xr = xAR(t);
  var cam = xr - L / 2;
  ctx.fillStyle = 'rgba(120,180,255,0.06)';
  ctx.fillRect(X(cam - VIEW_A / 2), 2, VIEW_A * S, gY - 2);
  ctx.strokeStyle = 'rgba(120,170,230,0.18)';
  ctx.strokeRect(X(cam - VIEW_A / 2), 2, VIEW_A * S, gY - 2);

  var st = bState(t);

  // A
  ctx.fillStyle = '#2b4059';
  rr(ctx, X(xr - L), gY - 11, L * S, 11, 2); ctx.fill();
  ctx.strokeStyle = 'rgba(140,190,240,0.5)'; ctx.lineWidth = 1;
  rr(ctx, X(xr - L), gY - 11, L * S, 11, 2); ctx.stroke();

  // B
  ctx.beginPath();
  ctx.arc(X(xr - L + st.s), gY - 5.5, 3.2, 0, Math.PI * 2);
  ctx.fillStyle = '#f5a524'; ctx.fill();

  // C
  var c = cState(t);
  ctx.fillStyle = '#2dd4bf';
  rr(ctx, X(c.x - 0.45), gY - 9, Math.max(4, 0.9 * S), 9, 1.5); ctx.fill();

  // 标尺
  ctx.fillStyle = 'rgba(125,145,170,0.6)';
  ctx.font = '9px -apple-system,sans-serif';
  ctx.textAlign = 'left';
  var vtxt = t < 0 ? 'A+B → 10 m/s' : (t >= T_STOP ? 'A+B ← 2 m/s' : 'A ' + st.vA.toFixed(1) + ' m/s · B ' + st.vB.toFixed(1) + ' m/s');
  ctx.fillText(vtxt, 4, 10);

  // 播放头标记
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(140,200,255,0.9)';
  ctx.fillText('传送带', X((BELT_X0 + BELT_X1) / 2), gY + 14);
}

/* =====================================================================
   时间轴
   ===================================================================== */
function drawTimeline(t) {
  var f = fit(cvT), ctx = f.ctx, W = f.W, H = f.H;
  var pad = 14;
  var S = (W - pad * 2) / (T_END - T_BEG);
  var X = function (x) { return pad + (x - T_BEG) * S; };
  var y = H * 0.52;

  ctx.clearRect(0, 0, W, H);

  // 轨道
  ctx.strokeStyle = '#1c2836'; ctx.lineWidth = 5; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();

  // 已播放
  var px = X(Math.min(Math.max(t, T_BEG), T_END));
  var g = ctx.createLinearGradient(pad, 0, W - pad, 0);
  g.addColorStop(0, '#2f7bb8'); g.addColorStop(1, '#3fc9b4');
  ctx.strokeStyle = g; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(px, y); ctx.stroke();

  // 关键事件
  var evs = [{ t: 0, c: '#5ee0cd', l: 'A↔C' }];
  for (var i = 0; i < hits.length; i++) evs.push({ t: hits[i].t, c: '#f5a524', l: '' + hits[i].n });
  evs.push({ t: T_STOP, c: '#8fd3ff', l: '停' });

  evs.forEach(function (e) {
    var x = X(e.t);
    ctx.beginPath(); ctx.arc(x, y, 2.6, 0, Math.PI * 2);
    ctx.fillStyle = '#0a0f16'; ctx.fill();
    ctx.strokeStyle = e.c; ctx.lineWidth = 1.4; ctx.stroke();
    if (e.l) {
      ctx.fillStyle = e.c; ctx.font = '600 9px -apple-system,sans-serif';
      ctx.textAlign = 'center'; ctx.fillText(e.l, x, y - 9);
    }
  });

  // 播放头
  ctx.beginPath(); ctx.arc(px, y, 5.5, 0, Math.PI * 2);
  ctx.fillStyle = '#eaf6ff'; ctx.fill();
  ctx.beginPath(); ctx.arc(px, y, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = '#2f7bb8'; ctx.fill();

  ctx.fillStyle = 'rgba(125,145,170,0.75)';
  ctx.font = '9px -apple-system,sans-serif';
  ctx.textAlign = 'left'; ctx.fillText(T_BEG.toFixed(1) + ' s', pad, H - 4);
  ctx.textAlign = 'right'; ctx.fillText(T_END.toFixed(0) + ' s', W - pad, H - 4);
}

/* =====================================================================
   主循环 / 控制 / 读数
   ===================================================================== */
var t = T_BEG, playing = true, speed = 0.35, lastNow = 0, frame = 0;
var btnPlay = document.getElementById('btnPlay');
var btnReset = document.getElementById('btnReset');
var spd = document.getElementById('spd');
var tval = document.getElementById('tval');
var roPhase = document.getElementById('roPhase');
var roGrid = document.getElementById('roGrid');

/* --- 读数格子 --- */
var CELLS = [
  { id: 'vA', k: 'v_A', u: 'm/s' },
  { id: 'vB', k: 'v_B', u: 'm/s' },
  { id: 'vC', k: 'v_C', u: 'm/s' },
  { id: 'uu', k: 'B 相对 A', u: 'm/s' },
  { id: 's', k: 'B 距 A 左端', u: 'm' },
  { id: 'd', k: 'B 距 A 右端', u: 'm' },
  { id: 'n', k: '碰撞次数', u: '' },
  { id: 'vc', k: '质心速度', u: 'm/s' }
];
var cellEls = {};
CELLS.forEach(function (c) {
  var d = document.createElement('div');
  d.className = 'cell';
  d.innerHTML = '<div class="k">' + c.k + '</div><div class="v" id="ro_' + c.id + '">—</div>';
  roGrid.appendChild(d);
  cellEls[c.id] = d.querySelector('.v');
});

function setCell(id, val, unit) {
  cellEls[id].innerHTML = val + (unit ? '<small>' + unit + '</small>' : '');
}

function signed(v) {
  if (Math.abs(v) < 0.005) return '0.00';
  return (v > 0 ? '+' : '−') + Math.abs(v).toFixed(2);
}

function phaseText(t) {
  var st = bState(t);
  if (t < 0) return 'A、B 正以 10 m/s 一起向右运动，B 靠在 A 凹槽的左端；C 静止在地面上。';
  if (t < 0.2) return 'A 与 C 发生弹性碰撞 —— A 立刻反弹：<b>5 m/s 向左</b>；C 以 <b>5 m/s 向右</b>滑出。B 的速度没变，仍是 10 m/s。';
  if (t >= T_STOP) return 'B 相对 A 终于停下：B 停在距 A 左端 3 m 处，此后 A、B 以 <b>2 m/s</b> 一起向左匀速运动（与 C 同速同向，不再相撞）。';
  if (Math.abs(st.u) < 0.06) return 'B 与 A 之间的相对速度已经减为 0，两者即将一起运动。';
  var dir = st.u > 0 ? '向右' : '向左';
  var text = 'B 相对 A ' + dir + '滑动，滑动摩擦让相对速度以 2.5 m/s² 均匀变小（此刻 ' +
    Math.abs(st.u).toFixed(2) + ' m/s）。';
  return text;
}

function render() {
  drawSceneA(t);
  drawSceneC(t);
  drawOverview(t);
  drawTimeline(t);

  tval.textContent = t.toFixed(2);

  {
    var st = bState(t), c = cState(t);
    setCell('vA', signed(st.vA), 'm/s');
    setCell('vB', signed(st.vB), 'm/s');
    setCell('vC', signed(c.v), 'm/s');
    setCell('uu', signed(st.u), 'm/s');
    setCell('s', st.s.toFixed(2), 'm');
    setCell('d', (L - st.s).toFixed(2), 'm');
    setCell('n', countHits(t) + ' / ' + hits.length, '');
    setCell('vc', t < 0 ? signed(10) : signed(VCM), 'm/s');
    roPhase.innerHTML = phaseText(t);
  }
  frame++;
}

/* rAF 在部分环境下会被节流，用 setInterval 兜底驱动 */
function loop(now) {
  if (!lastNow) lastNow = now;
  var dt = (now - lastNow) / 1000;
  if (dt <= 0) return;
  lastNow = now;
  if (dt > 0.12) dt = 0.12;
  if (playing) {
    t += dt * speed;
    if (t >= T_END) { t = T_END; playing = false; syncPlayBtn(); }
  }
  render();
}

function rafLoop() {
  loop(performance.now());
  requestAnimationFrame(rafLoop);
}

function syncPlayBtn() {
  btnPlay.textContent = playing ? '暂停' : (t >= T_END - 1e-6 ? '重播' : '播放');
}

btnPlay.addEventListener('click', function () {
  if (!playing && t >= T_END - 1e-6) { t = T_BEG; }
  playing = !playing;
  syncPlayBtn();
});

btnReset.addEventListener('click', function () {
  t = T_BEG; lastNow = 0; playing = true; syncPlayBtn();
});

spd.addEventListener('click', function (e) {
  var b = e.target.closest('button');
  if (!b) return;
  speed = parseFloat(b.dataset.s);
  Array.prototype.forEach.call(spd.querySelectorAll('button'), function (x) {
    x.classList.toggle('on', x === b);
  });
});

/* --- 时间轴拖动 --- */
var dragging = false;
function seekAt(clientX) {
  var r = cvT.getBoundingClientRect();
  var pad = 14;
  var frac = (clientX - r.left - pad) / (r.width - pad * 2);
  frac = Math.max(0, Math.min(1, frac));
  t = T_BEG + frac * (T_END - T_BEG);
  lastNow = 0;
}
cvT.addEventListener('pointerdown', function (e) {
  dragging = true;
  cvT.setPointerCapture(e.pointerId);
  seekAt(e.clientX);
});
cvT.addEventListener('pointermove', function (e) {
  if (dragging) seekAt(e.clientX);
});
cvT.addEventListener('pointerup', function (e) {
  dragging = false;
  try { cvT.releasePointerCapture(e.pointerId); } catch (err) {}
});

window.addEventListener('resize', function () { frame = 0; });

syncPlayBtn();
window.__seek=function(v){ t=Math.max(T_BEG,Math.min(T_END,v)); playing=false; lastNow=0; syncPlayBtn(); render(); };
render();
setInterval(function(){ loop(performance.now()); }, 33);
requestAnimationFrame(rafLoop);

})();
