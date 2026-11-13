"""Build or preview documentation with repository links resolved.

The committed sources are never modified: the config is rendered into a
temporary file next to it, so the sources never change.
"""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
RENDERED_CONFIG = ".zensical-build.toml"
ORIGIN_PREFIXES = ("https://github.com/", "git@github.com:", "ssh://git@github.com/")


def repository_slug():
    repository = os.environ.get("REPOSITORY") or os.environ.get("GITHUB_REPOSITORY")
    if not repository:
        origin = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True
        ).strip()
        for prefix in ORIGIN_PREFIXES:
            if origin.startswith(prefix):
                repository = origin.removeprefix(prefix).removesuffix(".git")
                break
        else:
            raise ValueError("Set REPOSITORY=owner/repo when origin is not a GitHub URL")
    if not SLUG.fullmatch(repository):
        raise ValueError("REPOSITORY must have the form owner/repo")
    return repository


@contextmanager
def prepared_config(repository):
    """Yield a rendered copy of zensical.toml; the committed source stays untouched.

    Zensical resolves paths relative to the config file and requires site_dir
    inside the project root, so the copy lives in the root and is removed after.
    """
    text = (ROOT / "zensical.toml").read_text().replace("{repository}", repository)
    config = ROOT / RENDERED_CONFIG
    config.write_text(text)
    try:
        yield config
    finally:
        config.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "serve"))
    args, extra = parser.parse_known_args()
    with prepared_config(repository_slug()) as config:
        return subprocess.call(
            [sys.executable, "-m", "zensical", args.command, "-f", str(config), *extra],
            cwd=ROOT,
        )


if __name__ == "__main__":
    sys.exit(main())
