"""Build or preview documentation with repository links resolved."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[1]


def repository_slug():
    repository = os.environ.get("REPOSITORY") or os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        origin = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True
        ).strip()
        match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?", origin)
        if not match:
            raise ValueError("Set REPOSITORY=owner/repo when origin is not a GitHub URL")
        repository = match[1]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("REPOSITORY must have the form owner/repo")
    return repository


@contextmanager
def prepared_sources(repository):
    config = ROOT / "zensical.toml"
    index = ROOT / "docs/index.md"
    originals = {path: path.read_bytes() for path in (config, index)}
    rendered_config = originals[config].decode().replace("{repository}", repository)
    rendered_index = Template(originals[index].decode(), undefined=StrictUndefined).render(
        config=tomllib.loads(rendered_config)["project"]
    ) + "\n"
    rendered = {config: rendered_config.encode(), index: rendered_index.encode()}
    try:
        for path, content in rendered.items():
            path.write_bytes(content)
        yield
    finally:
        for path, original in originals.items():
            # Preserve edits made by the user while a preview was running.
            if path.read_bytes() == rendered[path]:
                path.write_bytes(original)
            else:
                print(f"Source changed during preview; leaving {path} intact", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "serve"))
    args, extra = parser.parse_known_args()
    with prepared_sources(repository_slug()):
        return subprocess.call(
            [sys.executable, "-m", "zensical", args.command, *extra], cwd=ROOT
        )


if __name__ == "__main__":
    sys.exit(main())
