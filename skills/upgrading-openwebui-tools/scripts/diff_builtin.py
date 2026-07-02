#!/usr/bin/env python3
"""Diff an old Open WebUI builtin.py against the installed one.

Usage: python diff_builtin.py <OLD_VERSION>   e.g. 0.9.2

Fetches the old builtin.py from GitHub raw at tag v<OLD_VERSION> and diffs it
against the copy in .venv. Prints the section banners (for the mapping table),
a filtered view of changed def/class/await lines, and the full unified diff.
Import reordering is cosmetic — focus on signature and behavior changes.
"""
import difflib
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW_URL = (
    "https://raw.githubusercontent.com/open-webui/open-webui/"
    "v{ver}/backend/open_webui/tools/builtin.py"
)


def find_installed_builtin() -> Path:
    """Locate builtin.py inside the local .venv, whatever the python version dir."""
    matches = list(Path(".venv/lib").glob("python*/site-packages/open_webui/tools/builtin.py"))
    if not matches:
        sys.exit("Could not find installed builtin.py under .venv/lib/python*/...")
    return matches[0]


def fetch_old(ver: str) -> str:
    url = RAW_URL.format(ver=ver)
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        sys.exit(f"Failed to fetch {url}: {e}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    old_ver = sys.argv[1]

    new_path = find_installed_builtin()
    new_text = new_path.read_text()
    old_text = fetch_old(old_ver)

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    print(f"=== builtin.py sections in installed version ({new_path}) ===")
    for i, line in enumerate(new_lines):
        if line.strip().startswith("#") and line.strip().strip("#").strip().isupper():
            title = line.strip().strip("#").strip()
            if title:
                print(f"  line {i + 1}: {title}")

    diff = list(difflib.unified_diff(old_lines, new_lines, f"v{old_ver}", "installed"))

    print("\n=== changed def / class / await lines (signal) ===")
    sig = re.compile(r"^[+-].*(def |class |async def |await )")
    for line in diff:
        if sig.match(line) and not line.startswith(("+++", "---")):
            print(line.rstrip())

    print("\n=== full unified diff (ignore import reordering) ===")
    sys.stdout.writelines(diff)


if __name__ == "__main__":
    main()
