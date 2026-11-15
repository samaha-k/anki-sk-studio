function svInit(root, dotChar) {
  if (!root) return;
  var old = document.querySelectorAll('.sv-lb');
  for (var o = 0; o < old.length; o++) old[o].parentNode.removeChild(old[o]);

  var d = root.querySelector('.dots');
  if (d) { var n = parseInt(d.getAttribute('data-n'), 10) || 0, s = ''; for (var i = 0; i < n; i++) s += dotChar; d.textContent = s; }

  var q = root.querySelector('.qtext'), tp = root.querySelector('.sv-topic');
  if (q && tp) tp.textContent.split('|').forEach(function (t) {
    t = t.trim(); if (!t) return;
    for (var k = 0; k < q.childNodes.length; k++) {
      var nd = q.childNodes[k]; if (nd.nodeType !== 3) continue;
      var at = nd.nodeValue.toLowerCase().indexOf(t.toLowerCase()); if (at < 0) continue;
      var mid = nd.splitText(at); mid.splitText(t.length);
      var m = document.createElement('span'); m.className = 'topic'; m.textContent = mid.nodeValue;
      q.replaceChild(m, mid); break;
    }
  });

  // empty <div><br></div> leftovers inside a hook add blank lines to the sticky note: hide them (field text is untouched)
  var hk = root.querySelector('.hook');
  if (hk) Array.prototype.forEach.call(hk.querySelectorAll('div'), function (dv) { if (!dv.textContent.replace(/[\s ]/g, '')) dv.style.display = 'none'; });

  var raw = root.querySelector('.raw');
  if (!raw) return;
  var grid = root.querySelector('.points'), fm = root.querySelector('.sv-formula');
  var fset = fm ? fm.textContent.split(/\s+/) : [];
  if (grid) {
    var lis = raw.querySelectorAll('li'), idx = 0;
    var parts = lis.length ? Array.prototype.map.call(lis, function (x) { return x.innerHTML; }) : raw.innerHTML.split(/<br\s*\/?>/i);
    parts.forEach(function (p) {
      p = p.replace(/^\s*•\s*/, '').trim(); if (!p) return;
      idx++;
      var box = document.createElement('div');
      box.className = 'pt' + (fset.indexOf(String(idx)) >= 0 ? ' formula' : '');
      box.style.setProperty('--i', idx - 1);
      box.innerHTML = '<span class="n">' + idx + '</span><div class="tx">' + p + '</div>';
      grid.appendChild(box);
    });
    root.style.setProperty('--n', idx);
  }
  raw.style.display = 'none';
  // v2: show an inline "[extra]" as a small bonus mark (display only; the field text is unchanged)
  Array.prototype.forEach.call(root.querySelectorAll('.tx'), function (t) {
    if (/\[extra\]/i.test(t.innerHTML)) t.innerHTML = t.innerHTML.replace(/\s*\[extra\]/gi, ' <span class="xb" title="Bonus: textbook, not slides">✦</span>');
  });

  var items = function () { return root.querySelectorAll('.pt, .cell'); };
  root.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target.closest('.pt, .cell') : null;
    if (t && root.contains(t)) { t.classList.toggle('hid'); sync(); }
  });
  var btn = root.querySelector('#sv-toggle');
  function sync() {
    if (!btn) return;
    var all = items(), h = 0; for (var i = 0; i < all.length; i++) if (all[i].classList.contains('hid')) h++;
    btn.textContent = h === all.length && all.length ? 'Show all' : 'Hide all';
  }
  if (btn) {
    if (!items().length) btn.style.display = 'none';
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var hide = btn.textContent === 'Hide all', all = items();
      for (var i = 0; i < all.length; i++) all[i].classList.toggle('hid', hide);
      sync();
    });
  }

  var imgs = root.querySelectorAll('.frame img');
  for (var j = 0; j < imgs.length; j++) (function (img) {
    var grow = function () {
      var w = img.naturalWidth; if (!w) return;
      if (w < 520) img.style.width = Math.round(w * 1.35) + 'px';
      else img.style.width = w + 'px';
    };
    if (img.complete) grow(); else img.addEventListener('load', grow);
    img.parentNode.addEventListener('click', function (e) {
      e.stopPropagation();
      var lb = document.createElement('div'); lb.className = 'sv-lb';
      lb.innerHTML = '<span class="x">✕</span>';
      var big = document.createElement('img'); big.src = img.src; lb.appendChild(big);
      lb.addEventListener('click', function (ev) { ev.stopPropagation(); lb.parentNode && lb.parentNode.removeChild(lb); });
      document.body.appendChild(lb);
    });
  })(imgs[j]);
}
