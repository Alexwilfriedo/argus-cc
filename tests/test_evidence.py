import json
import unittest
import test_report
from test_report import report


class EvidenceTest(unittest.TestCase):
    setUp = test_report.ReportTest.setUp
    junit = test_report.ReportTest.junit
    render = test_report.ReportTest.render

    def test_unreadable_result_preserves_other_target(self):
        self.junit('<testcase name="Période"/>')
        (self.base / 'web.json').write_text('{')
        web = {'label': 'Web', 'planned': ['Web'], 'playwright': 'web.json'}
        html = report.build_html(dict(title='Test', scope='Local', build='QA', targets=[web, self.target]), self.base)
        self.assertIn('1 / 2', html)
        self.assertIn('illisible', html)

    def test_mobile_evidence_cannot_count_twice(self):
        self.junit('<testcase name="Période"/>')
        html = report.build_html(dict(title='Test', scope='Local', build='QA',
                                      targets=[self.target, dict(self.target, label='iOS')]), self.base)
        self.assertIn('1 / 2', html)
        self.assertIn('déjà utilisé', html)

    def test_device_mismatch(self):
        self.junit('<testcase name="Période"/>')
        (self.base / 'target.txt').write_text('emulator-5582\nlocal.argus\n')
        self.target['device'] = 'sim-2'
        self.assertIn('0 / 1', self.render())

    def test_build_mismatch(self):
        self.junit('<testcase name="Période"/>')
        (self.base / 'build.txt').write_text('another-build')
        self.assertIn('0 / 1', self.render())

    def test_manual_nonexistent_file(self):
        self.target = dict(label='QA', planned=['Période'], observations=[
            dict(name='Période', status='pass', evidence='imaginaire.png')])
        self.assertIn('0 / 1', self.render())

    def test_documented_conflict_preserves_raw_result(self):
        self.junit('<testcase name="Période"/>')
        self.target['notes'] = {'Période': {'conflict': 'Story §2 autorise l’égalité. Contrat §4 la refuse.'}}
        html = self.render()
        self.assertIn('0 / 1', html)
        self.assertIn('Contrat §4', html)
        self.assertIn('Résultat brut', html)

    def test_junit_infrastructure_error(self):
        self.junit('<testcase name="Période"><error>Driver unavailable</error></testcase>', 1)
        self.assertIn('0 / 1', self.render())

    def test_playwright_expected_failure(self):
        test = dict(projectName='Web', expectedStatus='failed', status='expected', results=[dict(status='failed')])
        (self.base / 'web.json').write_text(json.dumps(dict(suites=[dict(title='f', specs=[dict(title='s', tests=[test])])])))
        self.target = dict(label='Web', planned=['Web › f › s'], playwright='web.json')
        html = self.render()
        self.assertIn('1 / 1', html)
        self.assertIn('Échec attendu', html)
        self.assertNotIn('Parcours vérifiés', html)

    def test_real_observation_and_conflicting_copy(self):
        (self.base / 'trace.txt').write_text('Écran visible')
        self.target = dict(label='QA', planned=['Période'], observations=[
            dict(name='Période', status='pass', evidence='trace.txt')])
        self.assertIn('Parcours vérifiés', self.render())
        self.target['observations'][0]['conflict'] = 'Story S2 et contrat C4'
        self.assertIn('0 / 1', self.render())

    def test_mobile_retry_preserves_first_failure(self):
        for name, case, code in [('first', '<failure/>', 1), ('second', '', 0)]:
            folder = self.base / name
            folder.mkdir()
            (folder / 'target.txt').write_text('emulator-1\nlocal.app\n')
            (folder / 'exit-code.txt').write_text(str(code))
            (folder / 'junit.xml').write_text(f'<testsuite><testcase name="Période">{case}</testcase></testsuite>')
        self.target['maestro'] = ['first', 'second']
        html = self.render()
        self.assertIn("class='flaky'", html)
        self.assertIn('1 / 1', html)
        self.assertNotIn('Parcours vérifiés', html)
