import contextlib
import io
import json
import logging
from pathlib import Path
import sys
import textwrap
import types
import unittest
from unittest.mock import Mock, patch


WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/security.yml'
SCRIPT = textwrap.dedent(
    WORKFLOW.read_text().split("          python - <<'PY'\n", 1)[1]
    .split('          PY\n', 1)[0]
)


class SecurityWorkflowTests(unittest.TestCase):
    def run_scan(self, results, warning=None, exit_code=None):
        logger = logging.getLogger('mobsfscan.mobsfscan')
        original_handlers = logger.handlers[:]

        def scan():
            if warning:
                logger.warning(warning)
            return results

        scanner = Mock()
        scanner.return_value.scan.side_effect = scan
        output = Mock()
        handle_exit = Mock()
        handle_exit.side_effect = SystemExit(exit_code) if exit_code else None
        modules = {}
        for name in ('mobsfscan', 'mobsfscan.__main__', 'mobsfscan.formatters', 'mobsfscan.mobsfscan'):
            modules[name] = types.ModuleType(name)
        modules['mobsfscan'].__version__ = '1.1.0'
        modules['mobsfscan.__main__'].handle_exit = handle_exit
        modules['mobsfscan.formatters'].sarif = types.SimpleNamespace(sarif_output=output)
        modules['mobsfscan.mobsfscan'].MobSFScan = scanner
        stderr = io.StringIO()
        status = 0
        with patch.dict(sys.modules, modules), contextlib.redirect_stderr(stderr):
            try:
                exec(compile(SCRIPT, str(WORKFLOW), 'exec'), {})
            except SystemExit as error:
                status = error.code
        self.assertEqual(logger.handlers, original_handlers)
        scanner.assert_called_once_with(['.'], True, 'android')
        return status, stderr.getvalue(), output, handle_exit

    def test_xml_warning_without_reported_errors_blocks_sarif(self):
        status, text, output, handle_exit = self.run_scan(
            {'results': {}, 'errors': []},
            '\x1b[33mAndroid XML checks failed. Please report to mobsfscan project\x1b[0m',
        )
        self.assertEqual(status, 1)
        self.assertIn('Incomplete MobSF scan', text)
        output.assert_not_called()
        handle_exit.assert_not_called()

    def test_reported_errors_print_sanitized_partial_findings(self):
        rule = 'rule\n::error::injected\x1b[31m'
        path = 'source\n::warning::injected.kt'
        results = {'errors': ['parser\nfailed'], 'results': {
            rule: {'files': [{'file_path': path, 'match_lines': [2, 3],
                              'match_string': 'SOURCE MUST NOT BE PRINTED'}]},
            'missing_control': {'metadata': {'description': 'DO NOT PRINT'}},
        }}
        status, text, output, handle_exit = self.run_scan(results)
        self.assertEqual(status, 1)
        self.assertIn('MobSF scan error: "parser\\nfailed"', text)
        self.assertIn('partial findings only (SARIF not generated)', text)
        summaries = [json.loads(line.removeprefix('Partial finding: '))
                     for line in text.splitlines() if line.startswith('Partial finding: ')]
        self.assertEqual(summaries, [
            {'rule_id': rule, 'locations': [{'path': path, 'lines': [2, 3]}]},
            {'rule_id': 'missing_control', 'locations': []},
        ])
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\n::', text)
        self.assertNotIn('SOURCE MUST NOT BE PRINTED', text)
        self.assertNotIn('DO NOT PRINT', text)
        output.assert_not_called()
        handle_exit.assert_not_called()

    def test_complete_scans_preserve_output_and_finding_exit_status(self):
        for warning, exit_code in ((None, None), ('Unrelated warning', None), (None, 1)):
            with self.subTest(warning=warning, exit_code=exit_code):
                results = {'results': {}, 'errors': []}
                status, text, output, handle_exit = self.run_scan(results, warning, exit_code)
                self.assertEqual(status, exit_code or 0)
                self.assertNotIn('Incomplete MobSF scan', text)
                output.assert_called_once_with('mobsfscan.sarif', results, '1.1.0', ['.'])
                handle_exit.assert_called_once_with(results, exit_warn=False, no_fail=False)


if __name__ == '__main__':
    unittest.main()
