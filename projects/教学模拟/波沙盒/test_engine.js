// 物理引擎验证脚本：跑稳态后检查干涉/衍射图样是否符合理论
global.window = global;
require('./engine.js');
var E = global.WaveEngine;

function peaks(arr) {
  // 找局部极大值（z 位置 + 值）
  var out = [], n = arr.length;
  for (var i = 1; i < n - 1; i++) {
    if (arr[i] > arr[i - 1] && arr[i] >= arr[i + 1] && arr[i] > 0.02 * Math.max.apply(null, arr)) {
      out.push({ z: i, v: arr[i] });
    }
  }
  return out;
}

function run(scene, params, steps) {
  var e = E.create();
  e.setScene(scene);
  for (var k in params) e.setParam(k, params[k]);
  // setParam 会 reset，所以最后一次性设置后直接跑
  for (var s = 0; s < steps; s++) e.step();
  return e;
}

// 但 setParam 每次都 rebuild+reset，多次调用会把之前参数保留（只 reset 场），OK
console.log('=== 双缝：λ=12, a=16, d=46, L=78 ===');
var e = run('double', { lambda: 12, a: 16, d: 46, screenDist: 78 }, 4000);
var pk = peaks(Array.prototype.slice.call(e.intensity));
var dz = [];
for (var i = 1; i < pk.length; i++) dz.push((pk[i].z - pk[i - 1].z).toFixed(1));
console.log('理论条纹间距 Δz = λL/d =', (12 * 78 / 46).toFixed(1), '格点');
console.log('实测峰值位置:', pk.map(function(p){return p.z;}));
console.log('相邻峰值间距:', dz);

console.log('\n=== 单缝：λ=12, a=16, L=78（衍射展宽，中央主极大）===');
var e2 = run('single', { lambda: 12, a: 16, screenDist: 78 }, 4000);
var pk2 = peaks(Array.prototype.slice.call(e2.intensity));
console.log('峰值位置:', pk2.map(function(p){return p.z + ':' + p.v.toFixed(3);}));
console.log('中央主极大 z≈', e2.meta.cz, '，首暗纹应在 z≈cz ± λL/a =', (12 * 78 / 16).toFixed(1), '格点');

console.log('\n=== 波长影响：双缝 λ=12 vs λ=20，条纹应变宽 ===');
var e3 = run('double', { lambda: 20, a: 16, d: 46, screenDist: 78 }, 4000);
var pk3 = peaks(Array.prototype.slice.call(e3.intensity));
var dz3 = [];
for (var i = 1; i < pk3.length; i++) dz3.push((pk3[i].z - pk3[i - 1].z).toFixed(1));
console.log('λ=20 理论间距 =', (20 * 78 / 46).toFixed(1), '格点；实测间距:', dz3);

console.log('\n=== 直边：edge=0.5（半无限挡板），几何阴影边界处应有衍射纹 ===');
var e4 = run('edge', { lambda: 12, edge: 0.5, screenDist: 78 }, 4000);
var it4 = Array.prototype.slice.call(e4.intensity);
var cut = Math.round(0.5 * e4.nz);
var bright = 0, dark = 0;
for (var z2 = cut - 12; z2 <= cut + 12; z2++) { if (it4[z2] > 0.5) bright++; else dark++; }
console.log('边界 z=', cut, '附近 25 格点内：亮区样本', bright, '，阴影区样本', dark);
console.log('阴影深处(z=cut-40)强度 =', it4[cut - 40].toFixed(3), '（应接近 0），开放区(z=cut+40)强度 =', it4[cut + 40].toFixed(3), '（应较大）');

console.log('\n=== 圆孔：D=40，中央亮斑，边缘衰减 ===');
var e5 = run('hole', { lambda: 12, D: 40, screenDist: 78 }, 4000);
var it5 = Array.prototype.slice.call(e5.intensity);
var cz = e5.meta.cz;
console.log('中心强度 =', it5[cz].toFixed(3), '；z=cz±30 强度 =', it5[cz + 30].toFixed(3), ',' + it5[cz - 30].toFixed(3), '（应明显小于中心）');
