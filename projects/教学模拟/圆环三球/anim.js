/* 三球圆环 —— 真实物理模拟（1D 环上匀速运动 + 完全弹性碰撞） */
(function () {
  'use strict';

  var cv = document.getElementById('cv');
  var ctx = cv.getContext('2d');
  var logEl = document.getElementById('log');
  var tval = document.getElementById('tval');
  var cycEl = document.getElementById('cyc');
  var nxtEl = document.getElementById('nxt');
  var fillEl = document.getElementById('fill');
  var playBtn = document.getElementById('play');

  var CIRC = 3;          // 周长 = 3 格（每格 1/3 圆周）
  var V0 = 1;            // A 的初速度 = 1（于是 Δ = 1 个时间单位）
  var IDX = ['Ⅰ', 'Ⅱ', 'Ⅲ'];

  var W = 700, H = 620, R = 180, cx = 420, cy = 320;

  var mod = function (x, n) { return ((x % n) + n) % n; };
  var phi = function (s) { return (-90 + s * 120) * Math.PI / 180; };
  var pt = function (s, rad) {
    var a = phi(s);
    return { x: cx + rad * Math.cos(a), y: cy + rad * Math.sin(a) };
  };

  /* ---------- 状态 ---------- */
  var T = 0, balls = [], flashes = [], running = true, speed = 1, jump = false;
  var lastT = 0;

  function fmt(u) {
    if (Math.abs(u) < 1e-9) return '0';
    var sg = u < 0 ? '−' : '', a = Math.abs(u);
    if (Math.abs(a - 1) < 1e-6) return sg + 'v';
    if (Math.abs(a - 1 / 3) < 1e-6) return sg + 'v/3';
    if (Math.abs(a - 2 / 3) < 1e-6) return sg + '2v/3';
    return sg + a.toFixed(2) + 'v';
  }
  function posName(s) { return IDX[mod(Math.round(s), 3)]; }
  function rgba(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  function addLog(html) {
    var li = document.createElement('li');
    li.innerHTML = html;
    logEl.insertBefore(li, logEl.firstChild);
    while (logEl.children.length > 26) logEl.removeChild(logEl.lastChild);
  }

  function reset() {
    balls = [
      { k: 'A', m: 1, s: 0, u: V0, c: '#d1483a' },
      { k: 'B', m: 2, s: 1, u: 0, c: '#3f648c' },
      { k: 'C', m: 2, s: 2, u: 0, c: '#3f648c' }
    ];
    T = 0; flashes = []; running = true; jump = false;
    latch = {};
    speed = parseFloat(document.getElementById('spd').value) || 1;
    logEl.innerHTML = '';
    playBtn.textContent = '暂停';
    addLog('<b>0Δ</b> A 以 <b>v</b> 从 Ⅰ 顺时针进入；2m 球静止在 Ⅱ、Ⅲ');
    lastT = 0;
  }

  /* ---------- 物理 ---------- */
  /* latch：一对球刚刚碰过、还没真正分开。分开之前不再判它们相撞，
     否则"碰后位移被吸附到等分点"会让两球一直重合，被误判成反复相撞 */
  var latch = {};

  function collide(i, j) {
    var a = balls[i], b = balls[j];
    var m1 = a.m, m2 = b.m, u1 = a.u, u2 = b.u;
    var v1 = ((m1 - m2) * u1 + 2 * m2 * u2) / (m1 + m2);
    var v2 = ((m2 - m1) * u2 + 2 * m1 * u1) / (m1 + m2);
    a.u = v1; b.u = v2;
    a.s = mod(Math.round(a.s), CIRC);   // 碰撞点必在 Ⅰ/Ⅱ/Ⅲ 上，顺手消掉浮点误差
    b.s = a.s;
    flashes.push({ s: a.s, ts: performance.now() });
    var tag = (m1 === m2) ? '质量相等 ⇒ 速度互换' : 'm 撞 2m';
    addLog('<b>' + T.toFixed(1) + 'Δ</b> ' + posName(a.s) + '：' +
      a.k + '(' + fmt(u1) + ') 撞 ' + b.k + '(' + fmt(u2) + ') → ' +
      a.k + ':' + fmt(v1) + '，' + b.k + ':' + fmt(v2) +
      ' <span class="tag">' + tag + '</span>');
    latch[i + '-' + j] = true;
  }

  /* 两球有向间距（取短的，范围 ±CIRC/2） */
  function sep(A, B) {
    var d = mod(B.s - A.s, CIRC);
    return d > CIRC / 2 ? d - CIRC : d;
  }

  function nextCollision() {
    var best = null;
    for (var i = 0; i < balls.length; i++) {
      for (var j = i + 1; j < balls.length; j++) {
        var A = balls[i], B = balls[j];
        var key = i + '-' + j;
        if (latch[key]) {                     // 刚碰过：等它们真的分开再恢复判定
          if (Math.abs(sep(A, B)) < 1e-6) continue;
          latch[key] = false;
        }
        var dv = A.u - B.u;
        if (Math.abs(dv) < 1e-9) continue;
        var d = mod(B.s - A.s, CIRC);
        /* d≈0 只可能出现在"某步恰好停在碰撞瞬间"的情形，此时必须立刻碰，
           绝不能当成"已经错开、下一圈再说"，否则就会穿过去 */
        var tt = d < 1e-9 ? 0 : mod(d / dv, CIRC / Math.abs(dv));
        if (!best || tt < best.t) {
          best = { t: tt, i: i, j: j, s: mod(A.s + A.u * tt, CIRC) };
        }
      }
    }
    return best;
  }

  function advance(dt) {
    for (var i = 0; i < balls.length; i++) balls[i].s = mod(balls[i].s + balls[i].u * dt, CIRC);
    T += dt;
  }

  function step(dt) {
    var remain = dt, guard = 0;
    while (remain > 1e-12 && guard++ < 600) {
      var e = nextCollision();
      if (!e || e.t > remain + 1e-12) { advance(remain); return; }
      if (e.t > 0) { advance(e.t); remain -= e.t; }
      collide(e.i, e.j);
      if (jump) { jump = false; running = false; playBtn.textContent = '播放'; return; }
    }
  }

  /* ---------- 绘制 ---------- */
  function fit() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var r = cv.getBoundingClientRect();
    W = Math.max(260, r.width); H = Math.max(220, r.height);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    R = Math.min(W * 0.275, H * 0.315);
    cx = W * 0.60; cy = H * 0.515;
  }
  window.addEventListener('resize', fit);
  window.addEventListener('orientationchange', function () { setTimeout(fit, 120); });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, W, H);

    /* 圆环形窄槽 */
    ctx.lineWidth = 26; ctx.strokeStyle = '#e9edf4';
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 6.2832); ctx.stroke();
    ctx.lineWidth = 1.5; ctx.strokeStyle = '#a7b1c2';
    ctx.beginPath(); ctx.arc(cx, cy, R + 13, 0, 6.2832); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, R - 13, 0, 6.2832); ctx.stroke();

    /* 直管道 + 弹簧 */
    var yTop = cy - R, x1 = cx, x0 = x1 - 126;
    ctx.fillStyle = '#f2f5f9'; ctx.strokeStyle = '#a7b1c2'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.rect(x0, yTop - 11, x1 - x0, 22); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x0 + 8, yTop);
    for (var k = 1; k <= 9; k++) ctx.lineTo(x0 + 8 + k * 8, yTop + (k % 2 ? -7 : 7));
    ctx.stroke();

    /* 三等分点 */
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (var q = 0; q < 3; q++) {
      var a1 = pt(q, R - 16), a2 = pt(q, R + 16);
      ctx.strokeStyle = '#e0a68f'; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.moveTo(a1.x, a1.y); ctx.lineTo(a2.x, a2.y); ctx.stroke();
      var lp = pt(q, R + 36);
      ctx.fillStyle = '#c2542d'; ctx.font = 'bold 17px "Noto Sans CJK SC",serif';
      ctx.fillText(IDX[q], lp.x, lp.y);
    }

    /* 0Δ 构型残影 */
    if (document.getElementById('ghost') && document.getElementById('ghost').checked) {
      ctx.save();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = 'rgba(60,70,90,.45)'; ctx.lineWidth = 1.2;
      for (var gi = 0; gi < 3; gi++) {
        var gp = pt(gi, R);
        ctx.beginPath(); ctx.arc(gp.x, gp.y, 13, 0, 6.2832); ctx.stroke();
      }
      ctx.restore();
    }

    /* 运动的"尾迹" */
    ctx.lineCap = 'round';
    for (var i = 0; i < balls.length; i++) {
      var b = balls[i];
      if (Math.abs(b.u) < 1e-6) continue;
      var len = 0.10 + 0.07 * Math.min(Math.abs(b.u), 1);
      var s0 = b.u > 0 ? b.s - len : b.s;
      var s1 = b.u > 0 ? b.s : b.s + len;
      ctx.beginPath(); ctx.arc(cx, cy, R, phi(s0), phi(s1), false);
      ctx.strokeStyle = rgba(b.c, 0.20); ctx.lineWidth = 10; ctx.stroke();
    }

    /* 小球 */
    for (var n = 0; n < balls.length; n++) {
      var bb = balls[n], p = pt(bb.s, R);

      /* 方向箭头（沿切向，指向运动方向） */
      if (Math.abs(bb.u) > 1e-6) {
        var sg = bb.u > 0 ? 1 : -1;
        var sA = bb.s + sg * 0.052, sB = bb.s + sg * 0.092;
        var pa = pt(sA, R), pb = pt(sB, R);
        var ang = phi(bb.s);
        var dir = { x: -Math.sin(ang) * sg, y: Math.cos(ang) * sg };
        var per = { x: -dir.y, y: dir.x };
        ctx.strokeStyle = rgba(bb.c, 0.75); ctx.lineWidth = 2.4;
        ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(pb.x + dir.x * 7, pb.y + dir.y * 7);
        ctx.lineTo(pb.x - dir.x * 2 + per.x * 5, pb.y - dir.y * 2 + per.y * 5);
        ctx.lineTo(pb.x - dir.x * 2 - per.x * 5, pb.y - dir.y * 2 - per.y * 5);
        ctx.closePath(); ctx.fillStyle = rgba(bb.c, 0.8); ctx.fill();
      }

      /* 速度标签（放在环内，同点叠球时错开半径） */
      var dup = 0;
      for (var q2 = 0; q2 < n; q2++) {
        if (Math.abs(mod(balls[q2].s - bb.s + 1.5, CIRC) - 1.5) < 0.17) dup++;
      }
      var lab = pt(bb.s, R - 44 - dup * 34);
      var txt = fmt(bb.u);
      ctx.font = 'bold 13px "Liberation Mono","Noto Sans Mono CJK SC",monospace';
      ctx.lineWidth = 4; ctx.strokeStyle = '#fff';
      ctx.strokeText(txt, lab.x, lab.y);
      ctx.fillStyle = Math.abs(bb.u) < 1e-9 ? '#a4acb8' : '#2b303a';
      ctx.fillText(txt, lab.x, lab.y);

      ctx.beginPath(); ctx.arc(p.x, p.y, 13, 0, 6.2832);
      ctx.fillStyle = bb.c; ctx.fill();
      ctx.lineWidth = 1.2; ctx.strokeStyle = '#2c3542'; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = 'bold 12px -apple-system,sans-serif';
      ctx.fillText(bb.k, p.x, p.y + 0.5);
    }

    /* 碰撞闪光 */
    var now = performance.now();
    flashes = flashes.filter(function (f) { return now - f.ts < 560; });
    for (var f2 = 0; f2 < flashes.length; f2++) {
      var kk = (now - flashes[f2].ts) / 560;
      var pp = pt(flashes[f2].s, R);
      ctx.beginPath(); ctx.arc(pp.x, pp.y, 13 + kk * 30, 0, 6.2832);
      ctx.strokeStyle = 'rgba(194,84,45,' + (0.55 * (1 - kk)).toFixed(3) + ')';
      ctx.lineWidth = 3 * (1 - kk) + 0.6; ctx.stroke();
    }
  }

  /* ---------- 面板 ---------- */
  function panel() {
    tval.textContent = T.toFixed(2);
    fillEl.style.width = (mod(T, 15) / 15 * 100).toFixed(2) + '%';
    cycEl.textContent = String(Math.floor(T / 15) + 1);
    var e = nextCollision();
    if (!e) { nxtEl.textContent = '没有后续碰撞'; return; }
    var A = balls[e.i], B = balls[e.j];
    nxtEl.innerHTML = '下一次碰撞：<b>' + e.t.toFixed(2) + 'Δ</b> 后在 <b>' + posName(e.s) + '</b> 处，' +
      A.k + '(' + fmt(A.u) + ') 与 ' + B.k + '(' + fmt(B.u) + ')';
  }

  /* ---------- 主循环 ---------- */
  /* rAF 在后台标签页会被节流，配一个定时器兜底，两者都按真实时间推进 */
  function tick() {
    var now = performance.now();
    if (!lastT) lastT = now;
    var dt = (now - lastT) / 1000;
    lastT = now;
    if (dt > 0.08) dt = 0.08;
    if (dt < 0) dt = 0;
    if (running) step(dt * speed);
    draw();
    panel();
  }
  function loop() { tick(); requestAnimationFrame(loop); }
  setInterval(tick, 33);

  /* ---------- 交互 ---------- */
  playBtn.addEventListener('click', function () {
    running = !running;
    playBtn.textContent = running ? '暂停' : '播放';
  });
  document.getElementById('stepbtn').addEventListener('click', function () {
    jump = true;
    if (!running) { running = true; }
    playBtn.textContent = '暂停';
  });
  document.getElementById('reset').addEventListener('click', reset);
  document.getElementById('spd').addEventListener('change', function (e) {
    speed = parseFloat(e.target.value) || 1;
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.code === 'Space') { ev.preventDefault(); playBtn.click(); }
  });

  /* 调试接口（供自动化检查用） */
  window.__sim = {
    step: function (dt) { step(dt); draw(); panel(); },
    state: function () {
      return { T: T, balls: balls.map(function (b) { return { k: b.k, m: b.m, s: b.s, u: b.u }; }) };
    },
    pause: function () { running = false; playBtn.textContent = '播放'; },
    reset: reset
  };

  fit();
  reset();
  loop();
})();
