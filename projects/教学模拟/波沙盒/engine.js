/* ============================================================================
 * 波的干涉/衍射沙盒 · 惠更斯-菲涅尔原理直接叠加（无波动方程，无反射）
 * ----------------------------------------------------------------------------
 * 平面波照到挡板/障碍物，开口处每一点是次级子波源（惠更斯子波），带倾斜因子：
 *   u(x,z,t) = Σ_s  A_s·K(θ)·cos(k·r_s + φ0 − ωt) / √r_s
 *   K(θ) = (1 + cosθ)/2    （倾斜因子：子波向前传播，抑制侧向/向后 → 无杂波）
 *
 * 性能：距离/相位与时间无关，参数变化时预计算一次 cos/sin 分量 C、S，
 * 每帧只需 u = C·cos(φ0−ωt) − S·sin(φ0−ωt)，两次乘法，实时 60fps。
 * 场景：单缝 / 双缝 / 多缝 / 直边（单侧边缘障碍物）/ 障碍物（有限挡块）。
 * ==========================================================================*/
(function (global) {
  'use strict';

  var DT = 0.3;    // 动画相位每步推进量（越小动画越慢）

  function create(opts) {
    opts = opts || {};
    var nx = opts.nx || 220;
    var nz = opts.nz || 170;
    var barX = opts.barX || 90;
    var srcX = opts.srcX || 20;

    var e = {
      nx: nx, nz: nz,
      barX: barX, srcX: srcX,
      scene: 'double',
      params: {
        lambda: 10, a: 12, d: 24, N: 3, H: 40, edge: 0.5, screenDist: 95, amplitude: 1
      },
      screenX: barX + 95,
      u: new Float32Array(nx * nz),
      solid: new Uint8Array(nx * nz),
      intensity: new Float32Array(nz),
      sources: [], sourceAmp: [],
      preC: null, preS: null,   // 预计算的 cos/sin 分量（右侧 W×nz）
      W: nx - barX,
      t: 0,
      meta: { cz: nz >> 1 }
    };

    function idx(x, z) { return z * nx + x; }

    function buildSolid() {
      var sol = e.solid;
      sol.fill(0);
      var cz = e.meta.cz, p = e.params;
      var z, k, c, y0, y1;
      if (e.scene === 'single') {
        y0 = Math.round(cz - p.a / 2); y1 = Math.round(cz + p.a / 2);
        for (z = 0; z < nz; z++) if (z < y0 || z > y1) sol[idx(barX, z)] = 1;
      } else if (e.scene === 'double' || e.scene === 'multi') {
        var n = (e.scene === 'multi') ? p.N : 2;
        for (z = 0; z < nz; z++) sol[idx(barX, z)] = 1;
        for (k = 0; k < n; k++) {
          c = cz + (k - (n - 1) / 2) * p.d;
          y0 = Math.round(c - p.a / 2); y1 = Math.round(c + p.a / 2);
          for (z = Math.max(0, y0); z <= Math.min(nz - 1, y1); z++) sol[idx(barX, z)] = 0;
        }
      } else if (e.scene === 'edge') {
        var cut = Math.round(p.edge * nz);
        for (z = 0; z < nz; z++) if (z <= cut) sol[idx(barX, z)] = 1;
      } else if (e.scene === 'obstacle') {
        y0 = Math.round(cz - p.H / 2); y1 = Math.round(cz + p.H / 2);
        for (z = 0; z < nz; z++) if (z >= y0 && z <= y1) sol[idx(barX, z)] = 1;
      }
    }

    // 边界渐变衰减：关闭（开放区两侧不应被人为削弱）
    function apod(z) {
      return 1;
    }

    // 预计算：C[z,dx]=Σ A·K·cos(kr)/√r，S[z,dx]=Σ A·K·sin(kr)/√r
    function precompute() {
      var k = 2 * Math.PI / e.params.lambda;
      var invSqrtLam = 1 / Math.sqrt(e.params.lambda);   // 惠更斯归一化：能量守恒
      var S = e.sources, A = e.sourceAmp, ns = S.length;
      var W = e.W;
      var C = new Float32Array(W * nz);
      var Ss = new Float32Array(W * nz);
      var z, dx, s, zs, r, K, amp, kr, i, re, im;
      for (z = 0; z < nz; z++) {
        for (dx = 0; dx < W; dx++) {
          re = 0; im = 0;
          for (s = 0; s < ns; s++) {
            zs = S[s];
            r = Math.sqrt(dx * dx + (z - zs) * (z - zs));
            if (r < 1) r = 1;
            K = 0.5 * (1 + dx / r);
            amp = A[s] * K / Math.sqrt(r) * invSqrtLam;
            kr = k * r;
            re += amp * Math.cos(kr);
            im += amp * Math.sin(kr);
          }
          i = z * W + dx;
          C[i] = re; Ss[i] = im;
        }
      }
      e.preC = C; e.preS = Ss;
    }

    function isSolidAt(zz) {
      var iz = zz < 0 ? 0 : (zz >= nz ? nz - 1 : zz);
      return e.solid[idx(barX, iz)];
    }

    function rebuild() {
      buildSolid();
      e.sources.length = 0; e.sourceAmp.length = 0;
      var EXT = 48;   // 子波源延伸出网格边界，避免边界处振幅被截断削弱
      for (var z = -EXT; z < nz + EXT; z++) {
        if (!isSolidAt(z)) {
          e.sources.push(z);
          e.sourceAmp.push(1);
        }
      }
      e.screenX = Math.min(nx - 2, barX + Math.round(e.params.screenDist));
      precompute();
      computeIntensity();
      e.t = 0;
      e.u.fill(0);
      stepField();
    }

    function computeIntensity() {
      var W = e.W, dx0 = e.screenX - barX;
      var C = e.preC, S = e.preS, it = e.intensity;
      var amp = e.params.amplitude, a2 = amp * amp;   // 强度 ∝ 振幅²
      for (var z = 0; z < nz; z++) {
        var i = z * W + dx0;
        it[z] = (C[i] * C[i] + S[i] * S[i]) * a2;
      }
    }

    function stepField() {
      var k = 2 * Math.PI / e.params.lambda;
      var omega = 2 * Math.PI / e.params.lambda;
      var t = e.t, u = e.u;
      var phi0 = k * (barX - srcX);
      var ct = Math.cos(phi0 - omega * t);
      var st = Math.sin(phi0 - omega * t);
      var C = e.preC, S = e.preS, W = e.W;
      var z, x, base, dx, i;
      var amp = e.params.amplitude;

      for (z = 0; z < nz; z++) {
        base = z * nx;
        for (x = 0; x < srcX; x++) u[base + x] = 0;
        for (x = srcX; x < barX; x++) u[base + x] = Math.cos(k * (x - srcX) - omega * t) * amp;
        for (dx = 0; dx < W; dx++) {
          i = z * W + dx;
          u[base + barX + dx] = (C[i] * ct - S[i] * st) * amp;
        }
        // 挡板/障碍物固体格点归零
        if (e.solid[base + barX]) u[base + barX] = 0;
      }
    }

    function step(mult) {
      e.t += DT * (mult || 1);
      stepField();
    }

    function setScene(name) {
      if (e.scene === name) return;
      e.scene = name;
      rebuild();
    }

    function setParam(name, value) {
      if (e.params[name] === value) return;
      e.params[name] = value;
      rebuild();
    }

    rebuild();

    e.step = step;
    e.setScene = setScene;
    e.setParam = setParam;
    e.rebuild = rebuild;
    e.stepField = stepField;
    return e;
  }

  global.WaveEngine = { create: create, DT: DT };
})(typeof window !== 'undefined' ? window : this);
