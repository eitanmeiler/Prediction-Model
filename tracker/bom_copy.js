// Bookmarklet: run on a boxofficemojo.com/year/YYYY/ page that YOU opened, after sorting by Theaters.
// Copies the visible table to the clipboard as tab-separated text (same as select + Cmd-C), tagged with the year.
(() => {
  const y = (location.pathname.match(/year\/(\d{4})/) || [])[1];
  if (!location.hostname.endsWith('boxofficemojo.com') || !y) { alert('Open a boxofficemojo.com/year/YYYY/ page first.'); return; }
  const t = [...document.querySelectorAll('table')].sort((a, b) => b.rows.length - a.rows.length)[0];
  if (!t) { alert('No table found on this page.'); return; }
  const rows = [...t.rows].map(r => [...r.cells].map(c => c.innerText.trim().replace(/\s+/g, ' ')).join('\t'));
  const hdr = rows[0].split('\t').map(h => h.trim());
  const ti = hdr.findIndex(h => h === 'Theaters' || h === 'Max Th' || h.startsWith('Max Th'));
  if (ti < 0) { alert('Could not find the Theaters column.'); return; }
  const th = rows.slice(1).map(r => parseInt((r.split('\t')[ti] || '').replace(/\D/g, '')) || 0);
  if (!th.every((v, i) => i === 0 || v <= th[i - 1])) {
    alert('Sort by theaters first: click the "Theaters" column header (largest first), then click this button again.'); return;
  }
  const smallest = th[th.length - 1];
  navigator.clipboard.writeText('#BOM_YEAR ' + y + '\n' + rows.join('\n')).then(
    () => alert(`Copied ${y}: ${rows.length - 1} films. Smallest theater count on page: ${smallest}.` +
      (smallest >= 600 ? '\n\nWARNING: still 600+, so some wide releases may be cut off. Tell Claude.' : '\n\nOK: every wide release is included.')),
    e => alert('Copy failed: ' + e));
})();
