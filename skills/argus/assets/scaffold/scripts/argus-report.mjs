#!/usr/bin/env node
/**
 * argus-report.mjs — transforme le JSON du reporter Playwright en rapport HTML Argus.
 *
 * Entrée  : test-results/results.json (reporter ['json'] de playwright.config.ts)
 * Sortie  : argus-report/report.html
 *
 * Sans dépendance externe (Node >= 18, ESM). Lancé via `npm run argus:report`.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';

const INPUT = process.env.ARGUS_JSON ?? 'test-results/results.json';
const OUT_DIR = 'argus-report';
const OUT_FILE = path.join(OUT_DIR, 'report.html');

if (!existsSync(INPUT)) {
  console.error(
    `[argus] ${INPUT} introuvable. Lance d'abord la suite (npm run argus:test) ` +
      'pour générer le rapport JSON, puis relance argus:report.',
  );
  process.exit(1);
}

const report = JSON.parse(readFileSync(INPUT, 'utf8'));

// --- Aplatissement récursif des suites → liste de cas (spec × projet) --------
/** @returns {Array<{title,file,project,status,durationMs,errors:string[],attachments:any[]}>} */
function flatten(suites, trail = []) {
  const out = [];
  for (const suite of suites ?? []) {
    const nextTrail = suite.title ? [...trail, suite.title] : trail;
    for (const spec of suite.specs ?? []) {
      for (const t of spec.tests ?? []) {
        const attempts = t.results ?? [];
        const last = attempts.at(-1) ?? {};
        const errors = [];
        for (const r of t.results ?? []) {
          for (const e of r.errors ?? []) if (e?.message) errors.push(stripAnsi(e.message));
          if (r.error?.message) errors.push(stripAnsi(r.error.message));
        }
        out.push({
          title: [...nextTrail, spec.title].join(' › '),
          file: spec.file ?? suite.file ?? '',
          project: t.projectName ?? '',
          status: resultStatus(t, last),
          durationMs: last.duration ?? 0,
          errors: [...new Set(errors)],
          attachments: (t.results ?? []).flatMap((r) => r.attachments ?? []),
        });
      }
    }
    out.push(...flatten(suite.suites, nextTrail));
  }
  return out;
}

function stripAnsi(s) {
  // eslint-disable-next-line no-control-regex
  return String(s).replace(/\x1b\[[0-9;]*m/g, '');
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function resultStatus(test, last) {
  if (test.status === 'skipped') return 'skipped';
  if (!last.status || last.status === 'interrupted') return 'unknown';
  if (test.status !== 'expected') return test.status ?? 'unknown';
  if (last.status === 'failed' && test.expectedStatus === 'failed') return 'xfail';
  return last.status === 'passed' ? 'expected' : 'unknown';
}

// --- Extraction des Core Web Vitals depuis les attachments -------------------
function readAttachmentJson(att) {
  try {
    if (att.body) return JSON.parse(Buffer.from(att.body, 'base64').toString('utf8'));
    if (att.path && existsSync(att.path)) return JSON.parse(readFileSync(att.path, 'utf8'));
  } catch {
    /* attachement illisible → ignoré */
  }
  return null;
}

const cases = flatten(report.suites);
const stats = report.stats ?? {};
const summary = {
  total: cases.length,
  passed: cases.filter((c) => c.status === 'expected').length,
  failed: cases.filter((c) => c.status === 'unexpected').length,
  flaky: cases.filter((c) => c.status === 'flaky').length,
  skipped: cases.filter((c) => c.status === 'skipped').length,
};
let gate = 'pass';
if (summary.failed || report.errors?.length) gate = 'fail';
else if (!summary.total || summary.passed !== summary.total) gate = 'incomplete';

// Une ligne par mesure et par cas, pour conserver les différences entre cibles.
const cwvRows = [];
for (const c of cases) {
  for (const att of c.attachments) {
    if (!/core-web-vitals/i.test(att.name ?? '')) continue;
    const data = readAttachmentJson(att);
    for (const metric of Object.values(data?.vitals ?? {})) {
      if (!Number.isFinite(metric?.value)) continue;
      const value = metric.name === 'CLS' ? metric.value.toFixed(3) : Math.round(metric.value) + ' ms';
      cwvRows.push(`<tr><td>${esc(c.project)} · ${esc(c.title)}</td><td>${esc(metric.name)}</td><td>${value}</td></tr>`);
    }
  }
}

const statusLabels = { unexpected: 'Échec', flaky: 'Instable', xfail: 'Échec attendu', unknown: 'Non vérifié' };
const findings = cases.filter(c => c.status !== 'expected' && c.status !== 'skipped');
const ok = cases.filter((c) => c.status === 'expected');

const metric = (label, value, cls = '') =>
  `<div class="metric ${cls}"><div class="v">${value}</div><div class="l">${label}</div></div>`;

const findingCards = findings.length
  ? findings
      .map((c) => {
        const label = statusLabels[c.status] ?? 'Non vérifié';
        return `<div class="card ${esc(c.status)}">
        <div class="card-h"><span class="badge ${esc(c.status)}">${label}</span> <strong>${esc(c.title)}</strong></div>
        <div class="meta">${esc(c.project)} · ${esc(c.file)} · ${Math.round(c.durationMs)} ms</div>
        ${c.errors.length ? `<pre>${esc(c.errors.join('\n\n'))}</pre>` : ''}
      </div>`;
      })
      .join('')
  : '<p class="muted">Aucun défaut classé parmi les cas enregistrés.</p>';

const okList = ok.length
  ? `<ul class="ok-list">${ok.map((c) => `<li>${esc(c.title)} <span class="muted">(${esc(c.project)})</span></li>`).join('')}</ul>`
  : '<p class="muted">Aucun test passant.</p>';

const html = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Argus — rapport QA</title>
<style>
  :root{--bg:#0f1115;--card:#181b22;--fg:#e7e9ee;--muted:#8b93a7;--ok:#2ecc71;--bad:#e85d26;--warn:#f1c40f;--line:#262b36}
  *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  .wrap{max-width:1100px;margin:0 auto;padding:32px 20px}
  h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:32px 0 12px;border-bottom:1px solid var(--line);padding-bottom:8px}
  .sub{color:var(--muted);margin-bottom:24px;font-size:13px}
  .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}
  .metric{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;text-align:center}
  .metric .v{font-size:26px;font-weight:700}.metric .l{color:var(--muted);font-size:12px;margin-top:4px}
  .metric.pass .v{color:var(--ok)}.metric.fail .v{color:var(--bad)}.metric.flaky .v{color:var(--warn)}
  .gate{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:700}
  .gate.incomplete{color:var(--warn)}.gate.pass{background:rgba(46,204,113,.15);color:var(--ok)}.gate.fail{background:rgba(232,93,38,.15);color:var(--bad)}
  table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
  th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}
  td.good{color:var(--ok)}td.bad{color:var(--bad)}
  .card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--bad);border-radius:8px;padding:14px;margin-bottom:12px}
  .card.flaky{border-left-color:var(--warn)}
  .card-h{font-size:14px}.meta{color:var(--muted);font-size:12px;margin:6px 0}
  .badge{font-size:11px;text-transform:uppercase;padding:2px 8px;border-radius:999px;font-weight:700}
  .badge.unexpected{background:rgba(232,93,38,.18);color:var(--bad)}.badge.flaky{background:rgba(241,196,15,.18);color:var(--warn)}
  pre{background:#0b0d11;border:1px solid var(--line);border-radius:6px;padding:10px;overflow:auto;font-size:12px;white-space:pre-wrap}
  .ok-list{columns:2;gap:24px;list-style:none;padding:0}.ok-list li{margin:4px 0;break-inside:avoid}
  .muted{color:var(--muted)}footer{margin-top:40px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}
</style></head><body><div class="wrap">
  <h1>Argus — rapport QA</h1>
  <div class="sub">
    ${esc(report.config?.metadata?.argusBuild ?? '')} ·
    ${esc(stats.startTime ?? '')} ·
    ${Number.isFinite(stats.duration) ? `durée ${Math.round(stats.duration / 1000)} s` : 'durée non mesurée'} ·
    <span class="gate ${gate}">Bilan des tests · ${{ pass: 'réussis', fail: 'échec', incomplete: 'incomplet' }[gate]}</span>
  </div>

  <div class="metrics">
    ${metric('tests', summary.total)}
    ${metric('réussis', summary.passed, 'pass')}
    ${metric('échecs', summary.failed, 'fail')}
    ${metric('flaky', summary.flaky, 'flaky')}
    ${metric('ignorés', summary.skipped)}
  </div>

  ${cwvRows.length ? `<h2>Core Web Vitals</h2><table><tr><th>Cas</th><th>Métrique</th><th>Valeur</th></tr>${cwvRows.join('')}</table>` : ''}

  <h2>Résultats à examiner (${findings.length})</h2>
  ${report.errors?.length ? '<p>Erreur globale Playwright. Consulter le résultat brut du run.</p>' : ''}
  ${findingCards}

  <h2>Tests réussis (${ok.length})</h2>
  ${okList}

  <footer>Généré par Argus (Claude Code) · ${esc(stats.startTime ?? '')}</footer>
</div></body></html>`;

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(OUT_FILE, html, 'utf8');
console.log(`[argus] rapport écrit : ${OUT_FILE}`);
console.log(`[argus] ouvrir : open ${OUT_FILE}   (ou: xdg-open / start)`);
