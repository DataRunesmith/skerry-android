import ast
import itertools
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/wiki-sync.yml"
SCRIPT = textwrap.dedent(
    WORKFLOW.read_text(encoding="utf-8").split("          python3 <<'PY'\n", 1)[1]
    .split("          PY\n", 1)[0]
)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def scanner():
    module = ast.parse(SCRIPT)
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "find_links")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(WORKFLOW), "exec"), namespace)
    return namespace["find_links"]


def generate(index):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "docs").mkdir()
        (root / "docs/index.md").write_text(index, encoding="utf-8")
        environment = os.environ.copy()
        environment.update(REPOSITORY="example/project", DEFAULT_BRANCH="main")
        subprocess.run([sys.executable, "-c", SCRIPT], cwd=root, env=environment, check=True, timeout=10)
        return (root / "_wiki/Documentation.md").read_text(encoding="utf-8")


class WikiSyncTests(unittest.TestCase):
    def test_scanner_matches_original_expression(self):
        find_links = scanner()
        alphabet = "[]()a"
        for length in range(7):
            for chars in itertools.product(alphabet, repeat=length):
                value = "".join(chars)
                self.assertEqual(list(find_links(value)), LINK_PATTERN.findall(value), value)
        rng = random.Random(0)
        for _ in range(5000):
            value = "".join(rng.choices(alphabet + " \n", k=rng.randrange(100)))
            self.assertEqual(list(find_links(value)), LINK_PATTERN.findall(value), value)

    def test_navigation_filters_and_deduplicates(self):
        index = "\n".join([
            "[One](guide.md#section)", "[One](guide.md#other)",
            "[Folder](folder/)", "[[nested](nested.md)",
            "[Web](https://example.com)", "[Mail](mailto:a@example.com)",
            "[Anchor](#section)", "[Template]({{ value }})", "[Escape](../../outside.md)",
        ])
        output = generate(index)
        self.assertEqual(output.count("- **[One](https://github.com/example/project/blob/main/docs/guide.md)**"), 1)
        self.assertIn("- **[Folder](https://github.com/example/project/tree/main/docs/folder)**", output)
        self.assertIn("- **[[nested](https://github.com/example/project/blob/main/docs/nested.md)**", output)
        for label in ("Web", "Mail", "Anchor", "Template", "Escape"):
            self.assertNotIn(f"- **[{label}]", output)

    def test_adversarial_inputs_finish(self):
        generate("[" * 200000)
        generate("[x](" * 100000)
        output = generate("\n".join(f"[link{i}](file{i}.md)" for i in range(15000)))
        self.assertIn("[link14999](https://github.com/example/project/blob/main/docs/file14999.md)", output)


if __name__ == "__main__":
    unittest.main()
