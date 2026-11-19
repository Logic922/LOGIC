global.window = global;
require('./engine.js');
var E = global.WaveEngine;

function run(scene, params) {
  var e = E.create(); e.setScene(scene);
  for (var k in params) e.setParam(k, params[k]);
  return e;
}

// 双缝
var e = run('double', { a: 12, d: 24, screenDist: 95 });
var it = Array.prototype.slice.call(e.intensity);
var mx = 0, i;
for (i = 0; i < it.length; i++) if (it[i] > mx) mx = it[i];
var pk = [];
for (i = 1; i < it.length - 1; i++) if (it[i] > it[i - 1] && it[i] >= it[i + 1] && it[i] > 0.3 * mx) pk.push(i);
var dz = [];
for (i = 1; i < pk.length; i++) dz.push(pk[i] - pk[i - 1]);
console.log('双缝亮纹 z =', pk.join(','));
console.log('间距 =', dz.join(','), '（理论 λL/d = 39.6）');

// 单缝
var e2 = run('single', { a: 16, screenDist: 95 });
var it2 = Array.prototype.slice.call(e2.intensity);
var mx2 = 0;
for (i = 0; i < it2.length; i++) if (it2[i] > mx2) mx2 = it2[i];
console.log('单缝 a16: 中央(85)=' + it2[85].toFixed(2), '最大=' + mx2.toFixed(2), '（应中央最亮）');

// 直边
var e3 = run('edge', { edge: 0.5, screenDist: 95 });
var it3 = Array.prototype.slice.call(e3.intensity);
var cut = Math.round(0.5 * e3.nz);
console.log('直边: 阴影深(z=cut-40)=' + it3[cut - 40].toFixed(3), '开放区(z=cut+40)=' + it3[cut + 40].toFixed(3), '（阴影应≈0，开放区大）');

// 波场左右
var u = e.u, nx = e.nx, leftMax = 0, rightMax = 0, z, x;
for (z = 0; z < e.nz; z++) for (x = 0; x < e.barX; x++) { var a = Math.abs(u[z * nx + x]); if (a > leftMax) leftMax = a; }
for (z = 0; z < e.nz; z++) for (x = e.barX; x < nx; x++) { var a = Math.abs(u[z * nx + x]); if (a > rightMax) rightMax = a; }
console.log('左侧波场 max =', leftMax.toFixed(4), '（应=0）右侧 max =', rightMax.toFixed(2));
