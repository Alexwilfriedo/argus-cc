import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_report import SKILL


class HtmlReportTest(unittest.TestCase):
    def render(self, tests, errors=()):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = {"errors": errors, "suites": [{"title": "Example", "specs": [{"title": "Case", "tests": tests}]}]}
            path = root / "results.json"
            path.write_text(json.dumps(result))
            subprocess.run(["node", str(SKILL / "assets/scaffold/scripts/argus-report.mjs")],
                           cwd=root, env={**os.environ, "ARGUS_JSON": str(path)},
                           stdout=subprocess.DEVNULL, check=True)
            return (root / "argus-report/report.html").read_text()

    def test_no_attempt_has_no_claim_of_success(self):
        page = self.render([{"status": "expected"}])
        self.assertIn("Bilan des tests · incomplet", page)
        self.assertIn("Non vérifié</span>", page)

    def test_failure_requires_product_triage(self):
        page = self.render([{"status": "unexpected", "results": [{"status": "failed"}]}])
        self.assertIn("Bilan des tests · échec", page)
        self.assertIn(">Échec</span>", page)
        self.assertNotIn('>critical</span>', page)

    def test_global_error_is_visible_without_test_failures(self):
        page = self.render([], errors=[{"message": "fixture"}])
        self.assertIn("Bilan des tests · échec", page)
        self.assertIn("Erreur globale Playwright", page)
