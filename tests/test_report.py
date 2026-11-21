"""Regression checks for the campaign verdict; run with unittest discovery."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json

SKILL = Path(__file__).resolve().parents[1] / "skills" / "argus"
spec = importlib.util.spec_from_file_location("report", SKILL / "scripts" / "report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.target = {"label": "Android", "planned": ["Période"], "maestro": "."}

    def render(self):
        return report.build_html({"title": "A < B", "scope": "Local", "build": "QA",
                                  "targets": [self.target]}, self.base)

    def junit(self, cases, code=0):
        (self.base / "exit-code.txt").write_text(str(code))
        (self.base / "junit.xml").write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>")

    def test_absent_or_empty_results(self):
        for empty_junit in (False, True):
            if empty_junit:
                self.junit("")
            result = self.render()
            self.assertIn("À examiner", result)
            self.assertIn("0 / 1", result)

    def test_planned_and_extra_cases(self):
        self.junit('<testcase name="Période"/><testcase name="Extra"/>')
        result = self.render()
        self.assertIn("Parcours vérifiés", result)
        self.assertIn("1 / 1", result)
        self.assertIn("A &lt; B", result)
        self.assertIn("Extra", result)

    def test_failure_skip_and_driver_exit(self):
        for case, code, verdict in [
            ('<testcase name="Période"><failure/></testcase>', 1, "Échecs observés"),
            ('<testcase name="Période"><skipped/></testcase>', 0, "À examiner"),
            ('<testcase name="Période"/>', 1, "À examiner"),
        ]:
            self.junit(case, code)
            self.assertIn(verdict, self.render())

    def test_playwright_retry_counts_once(self):
        results = {"suites": [{"title": "dates", "specs": [{"title": "égalité", "tests": [
            {"projectName": "Web", "status": "flaky", "results": [
                {"status": "failed"}, {"status": "passed"}]}]}]}]}
        (self.base / "web.json").write_text(json.dumps(results))
        self.target = {"label": "Web", "planned": ["Web › dates › égalité"], "playwright": "web.json"}
        result = self.render()
        self.assertIn("À examiner", result)
        self.assertIn("1 / 1", result)
        self.assertIn("class='flaky'", result)

    def test_manual_pass_requires_evidence(self):
        self.target = {"label": "Relecture", "planned": ["Période"],
                       "observations": [{"name": "Période", "status": "pass"}]}
        with self.assertRaisesRegex(ValueError, "preuve"):
            self.render()

    def test_driver_exit_without_junit_preserves_reason(self):
        (self.base / "exit-code.txt").write_text("9")
        result = self.render()
        self.assertIn("code 9", result)
        self.assertIn("JUnit manquant", result)
        self.assertIn("0 / 1", result)
