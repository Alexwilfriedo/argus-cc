"""Build an offline PDF from a campaign plan and the results of its own run."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET


LABEL = {"pass": "Réussi", "fail": "Échec", "flaky": "Instable",
         "skip": "Ignoré", "blocked": "Non vérifié"}


def add(results, name, status):
    if not name or name in results:
        raise ValueError(f"Nom de scénario vide ou en double ({name})")
    results[name] = status


def mobile_results(folder):
    cases = {}
    issues = []
    code = (folder / "exit-code.txt").read_text().strip()
    if code != "0":
        issues.append(f"Maestro a terminé avec le code {code}.")
    junit = folder / "junit.xml"
    if not junit.exists():
        return cases, [*issues, "Rapport JUnit manquant."]
    root = ET.parse(junit).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Format JUnit inconnu")
    suite_error = False
    for suite in root.iter("testsuite"):
        if suite.get("errors", "0") != "0" or suite.get("failures", "0") != "0":
            suite_error = True
    for case in root.iter("testcase"):
        reported = case.get("status", "").upper()
        status = {"": "pass", "SUCCESS": "pass", "PASSED": "pass", "FAILED": "fail",
                  "FAILURE": "fail", "ERROR": "fail", "SKIPPED": "skip"}.get(reported, "blocked")
        if case.find("failure") is not None or case.find("error") is not None:
            status = "fail"
        elif case.find("skipped") is not None:
            status = "skip"
        add(cases, case.get("name"), status)
    if suite_error and "fail" not in cases.values():
        issues.append("La suite JUnit signale une erreur hors des cas rapportés.")
    return cases, issues


def web_results(path):
    report = json.loads(path.read_text())
    cases = {}
    issues = ["Playwright a signalé une erreur globale."] if report.get("errors") else []

    def visit(suite, parents):
        parents = [*parents, suite["title"]]
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                name = " › ".join(filter(None, [test.get("projectName"), *parents, spec["title"]]))
                attempts = test.get("results", [])
                status = {"unexpected": "fail", "flaky": "flaky", "skipped": "skip"}.get(test["status"], "blocked")
                if test["status"] == "expected" and attempts:
                    status = "pass" if attempts[-1]["status"] == "passed" else "skip"
                add(cases, name, status)
        for child in suite.get("suites", []):
            visit(child, parents)

    for suite in report["suites"]:
        visit(suite, [])
    return cases, issues


def read_target(target, base):
    plan = target["planned"]
    if not isinstance(plan, list) or not plan or len(plan) != len(set(plan)):
        raise ValueError("Chaque cible demande une liste planned de noms distincts.")
    sources = [kind for kind in ("maestro", "playwright", "observations") if kind in target]
    if len(sources) != 1:
        raise ValueError("Choisir une source de résultats par cible.")
    kind = sources[0]
    source = target[kind]
    if kind == "observations":
        cases = {}
        for observation in source:
            status = observation["status"]
            if status not in LABEL:
                raise ValueError(f"Statut inconnu ({status})")
            if status in {"pass", "fail", "flaky"} and not observation.get("evidence"):
                raise ValueError("Une observation exécutée demande une preuve.")
            add(cases, observation["name"], status)
        return cases, [], "Observations"
    try:
        reader = mobile_results if kind == "maestro" else web_results
        cases, issues = reader(base / source)
    except FileNotFoundError:
        cases, issues = {}, ["Pièce d’exécution manquante."]
    if not cases:
        issues.append("Aucun scénario enregistré.")
    return cases, issues, source


def h(value):
    return escape(str(value))


def screenshot(base, relative):
    path = (base / relative).resolve()
    if base.resolve() not in path.parents or path.suffix.lower() != ".png":
        raise ValueError("Choisir une capture PNG dans le dossier de la campagne.")
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Capture PNG illisible ({relative})")
    encoded = base64.b64encode(data).decode("ascii")
    return f'<img alt="Capture du constat" src="data:image/png;base64,{encoded}">'


def build_html(campaign, base):
    totals = Counter()
    sections = []
    planned = reached = 0
    all_issues = []
    if not campaign["targets"]:
        raise ValueError("La campagne demande au moins une cible.")
    for target in campaign["targets"]:
        cases, issues, source = read_target(target, base)
        names = target["planned"]
        reached += sum(cases.get(name) in {"pass", "fail", "flaky"} for name in names)
        planned += len(names)
        all_issues.extend(issues)
        notes = dict(target.get("notes", {}))
        if "observations" in target:
            for obs in target["observations"]:
                notes[obs["name"]] = {**notes.get(obs["name"], {}), **obs}
        names = list(dict.fromkeys([*names, *cases]))
        priority = {"fail": 0, "blocked": 1, "flaky": 2, "skip": 3, "pass": 4}
        names.sort(key=lambda name: priority[cases.get(name, "blocked")])
        rows = []
        for name in names:
            status = cases.get(name, "blocked")
            totals[status] += 1
            note = notes.get(name, {})
            details = []
            for key, label in (("severity", "Sévérité"), ("expected", "Attendu"),
                               ("actual", "Observé"), ("repro", "Reproduire"),
                               ("evidence", "Preuve"), ("action", "Suite")):
                if note.get(key):
                    details.append(f"<div><b>{label}</b> {h(note[key])}</div>")
            if note.get("screenshot"):
                details.append(screenshot(base, note["screenshot"]))
            rows.append(f"<tr><td><strong>{h(name)}</strong>{''.join(details)}</td>"
                        f"<td class='{status}'>{LABEL[status]}</td></tr>")
        warnings = "".join(f"<p class='blocked'>{h(issue)}</p>" for issue in issues)
        sections.append(f"<section><h2>{h(target['label'])}</h2><small>{h(source)}</small>"
                        f"{warnings}<table><thead><tr><th>Scénario et constats</th><th>Résultat</th>"
                        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></section>")
    if totals["fail"]:
        verdict = "Échecs observés"
    elif all_issues or totals["blocked"] or totals["skip"] or totals["flaky"]:
        verdict = "À examiner"
    else:
        verdict = "Parcours vérifiés"
    cards = "".join(f"<div><strong>{totals[key]}</strong>{label}</div>" for key, label in LABEL.items())
    css = Path(__file__).with_name("report.css").read_text()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>Argus · Rapport de tests</title><style>{css}</style></head><body>
<header>ARGUS <span>Rapport de tests</span></header><h1>{h(campaign['title'])}</h1>
<p>{h(campaign['scope'])}</p><small>Version testée · {h(campaign['build'])}</small>
<h2>{verdict}</h2><div class="metrics">{cards}</div>
<p><b>{reached} / {planned}</b> scénarios prévus avec un résultat de test.</p>
{''.join(sections)}<footer>Argus · Document généré le {generated}</footer></body></html>"""


def export(html, output):
    chrome = os.environ.get("ARGUS_CHROME") or next((path for name in
        ("google-chrome", "chromium", "chromium-browser", "chrome") if (path := shutil.which(name))), None)
    if not chrome:
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not Path(chrome).is_file():
        raise ValueError("Définir ARGUS_CHROME avec le chemin de Chrome ou Chromium.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp:
        work = Path(temp).resolve()
        page = work / "report.html"
        page.write_text(html, encoding="utf-8")
        pdf = work / "report.pdf"
        subprocess.run([chrome, "--headless", "--disable-gpu", "--disable-background-networking",
                        "--no-pdf-header-footer", f"--user-data-dir={work / 'profile'}",
                        f"--print-to-pdf={pdf}", page.as_uri()], check=True, timeout=90)
        if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
            raise ValueError("Le navigateur n’a pas produit de PDF.")
        pdf.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".pdf":
        parser.error("Choisir un fichier de sortie .pdf.")
    try:
        campaign = json.loads(args.campaign.read_text(encoding="utf-8"))
        export(build_html(campaign, args.campaign.parent), args.output)
    except (OSError, KeyError, TypeError, ValueError, ET.ParseError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Rapport Argus interrompu · {error}\n")
    print(args.output)


if __name__ == "__main__":
    main()
