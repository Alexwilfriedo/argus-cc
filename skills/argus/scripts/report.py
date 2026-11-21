"""Build an offline PDF from a campaign plan and the results of its own run."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
from html import escape
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET


LABEL = {"pass": "Réussi", "fail": "Échec", "flaky": "Instable",
         "skip": "Ignoré", "blocked": "Non vérifié", "xfail": "Échec attendu"}


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
                  "FAILURE": "fail", "ERROR": "blocked", "SKIPPED": "skip"}.get(reported, "blocked")
        if case.find("error") is not None:
            status = "blocked"
            issues.append(f"Erreur d’exécution · {case.get('name')}")
        elif case.find("failure") is not None:
            status = "fail"
        elif case.find("skipped") is not None:
            status = "skip"
        add(cases, case.get("name"), status)
    if suite_error and "fail" not in cases.values():
        issues.append("La suite JUnit signale une erreur hors des cas rapportés.")
    return cases, issues


def web_results(path, build):
    report = json.loads(path.read_text())
    cases = {}
    issues = ["Playwright a signalé une erreur globale."] if report.get("errors") else []

    recorded = report.get("config", {}).get("metadata", {}).get("argusBuild")
    if recorded and recorded != build:
        return {}, ["Le build consigné par Playwright diffère du manifeste."]

    def visit(suite, parents):
        parents = [*parents, suite["title"]]
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                name = " › ".join(filter(None, [test.get("projectName"), *parents, spec["title"]]))
                attempts = test.get("results", [])
                status = {"unexpected": "fail", "flaky": "flaky", "skipped": "skip"}.get(test["status"], "blocked")
                if status != "skip" and (not attempts or attempts[-1]["status"] == "interrupted"):
                    status = "blocked"
                elif test["status"] == "expected" and test.get("expectedStatus") == "failed" and attempts[-1]["status"] == "failed":
                    status = "xfail"
                elif test["status"] == "expected" and attempts:
                    status = "pass" if attempts[-1]["status"] == "passed" else "skip"
                add(cases, name, status)
        for child in suite.get("suites", []):
            visit(child, parents)

    for suite in report["suites"]:
        visit(suite, [])
    return cases, issues


def local_evidence(base, reference):
    if not isinstance(reference, str) or not reference.strip():
        return False
    path = (base / reference).resolve()
    return base.resolve() in path.parents and path.is_file() and path.stat().st_size > 0


def read_runs(kind, source, base, build, target, used):
    sources = source if isinstance(source, list) else [source]
    if not sources or (len(sources) > 1 and kind != "maestro"):
        raise ValueError("Choisir un JSON Playwright ou une suite de runs Maestro.")
    cases, issues, origins = {}, [], []
    first_device = None
    for ref in sources:
        folder = base / ref
        artifact = folder / "junit.xml" if kind == "maestro" else folder
        origins.append(ref)
        try:
            if kind == "maestro":
                identity = folder / "target.txt"
                device, app = identity.read_text().splitlines() if identity.exists() else ("", "")
                if device:
                    origins[-1] += f" · {device} · {app}"
                else:
                    origins[-1] += " · appareil non consigné"
                if (target.get("device", device) != device or target.get("appId", app) != app
                        or first_device is not None and first_device != (device, app)
                        or len(sources) > 1 and not (device and app)):
                    issues.append(f"{ref} · Identité de la cible incompatible ou absente.")
                    continue
                recorded = folder / "build.txt"
                if recorded.exists() and recorded.read_text().strip() != build:
                    issues.append(f"{ref} · Le build consigné par Maestro diffère du manifeste.")
                    continue
                current, warnings = mobile_results(folder)
            else:
                current, warnings = web_results(folder, build)
            issues.extend(warnings)
            if not current:
                continue
            fingerprint = (kind, hashlib.sha256(artifact.read_bytes()).digest())
            if fingerprint in used:
                issues.append(f"{ref} · Résultat déjà utilisé dans cette campagne.")
                continue
            used.add(fingerprint)
            if kind == "maestro":
                first_device = (device, app)
            for name, status in current.items():
                previous = cases.get(name)
                if status == "pass" and previous in {"fail", "flaky"}:
                    status = "flaky"
                elif status in {"skip", "blocked"} and previous in {"fail", "flaky"}:
                    status = previous
                cases[name] = status
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, ET.ParseError):
            issues.append(f"{ref} · Pièce d’exécution absente ou illisible.")
    if not cases:
        issues.append("Aucun scénario enregistré.")
    return cases, issues, " / ".join(origins)


def read_target(target, base, build, used):
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
        issues = []
        for observation in source:
            status = observation["status"]
            if status not in LABEL:
                raise ValueError(f"Statut inconnu ({status})")
            if status in {"pass", "fail", "flaky"} and not observation.get("evidence"):
                raise ValueError("Une observation exécutée demande une preuve.")
            if status in {"pass", "fail", "flaky", "xfail"} and not local_evidence(base, observation.get("evidence")):
                issues.append(f"{observation['name']} · Pièce justificative absente ou vide.")
                status = "blocked"
            add(cases, observation["name"], status)
        return cases, issues, "Observations consignées"
    return read_runs(kind, source, base, build, target, used)


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
    used = set()
    if not campaign["targets"]:
        raise ValueError("La campagne demande au moins une cible.")
    for target in campaign["targets"]:
        cases, issues, source = read_target(target, base, campaign["build"], used)
        names = target["planned"]
        planned += len(names)
        notes = dict(target.get("notes", {}))
        if "observations" in target:
            for obs in target["observations"]:
                notes[obs["name"]] = {**notes.get(obs["name"], {}), **obs}
        raw = cases.copy()
        for name, note in notes.items():
            if note.get("conflict"):
                cases[name] = "blocked"
        reached += sum(cases.get(name) in {"pass", "fail", "flaky", "xfail"} for name in names)
        names = list(dict.fromkeys([*names, *cases]))
        priority = {"fail": 0, "blocked": 1, "flaky": 2, "xfail": 3, "skip": 4, "pass": 5}
        names.sort(key=lambda name: priority[cases.get(name, "blocked")])
        rows = []
        for name in names:
            status = cases.get(name, "blocked")
            totals[status] += 1
            note = notes.get(name, {})
            details = []
            if note.get("conflict"):
                details.append(f"<div><b>À arbitrer</b> {h(note['conflict'])}</div>")
                details.append(f"<div><b>Résultat brut</b> {LABEL[raw.get(name, 'blocked')]}</div>")
            for key, label in (("severity", "Sévérité"), ("expected", "Attendu"),
                               ("actual", "Observé"), ("repro", "Reproduire"),
                               ("evidence", "Preuve"), ("action", "Suite")):
                if note.get(key):
                    details.append(f"<div><b>{label}</b> {h(note[key])}</div>")
            if note.get("screenshot"):
                try:
                    details.append(screenshot(base, note["screenshot"]))
                except (OSError, ValueError):
                    issues.append(f"{name} · Capture supplémentaire absente ou illisible.")
            rows.append(f"<tr><td><strong>{h(name)}</strong>{''.join(details)}</td>"
                        f"<td class='{status}'>{LABEL[status]}</td></tr>")
        all_issues.extend(issues)
        warnings = "".join(f"<p class='blocked'>{h(issue)}</p>" for issue in issues)
        sections.append(f"<section><h2>{h(target['label'])}</h2><small>Source · {h(source)}</small>"
                        f"{warnings}<table><thead><tr><th>Scénario et constats</th><th>Résultat</th>"
                        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></section>")
    if totals["fail"]:
        verdict = "Échecs observés"
    elif all_issues or totals["blocked"] or totals["skip"] or totals["flaky"] or totals["xfail"]:
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
<p>{h(campaign['scope'])}</p><small>Build déclaré · {h(campaign['build'])}</small>
<h2>{verdict}</h2><div class="metrics">{cards}</div>
<p><b>{reached} / {planned}</b> scénarios prévus avec un résultat exploitable.</p>
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
