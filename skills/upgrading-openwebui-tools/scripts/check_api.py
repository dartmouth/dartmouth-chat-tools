#!/usr/bin/env python3
"""Report the Open WebUI private-API surface a tool file depends on, and locate
each symbol's definition (with signature) in the installed package.

Usage: python check_api.py src/dartmouth_chat_tools/<file>.py

Extracts, from the target file:
  - `from open_webui... import ...` symbols (top-level AND lazy/in-function)
  - `await X.method(` call sites (the method names actually invoked)

For each, greps the installed .venv open_webui package for a matching
`def <name>` / `class <name>` and prints the definition line so you can eyeball
the signature and whether it is `async`.

Manual checks this does NOT do for you:
  - Whether an awaited call matches a sync/async definition
  - Whether call-site kwargs are still valid params
Treat the output as a checklist, not a verdict.
"""
import re
import subprocess
import sys
from pathlib import Path


def find_pkg_root() -> Path:
    matches = list(Path(".venv/lib").glob("python*/site-packages/open_webui"))
    if not matches:
        sys.exit("Could not find installed open_webui under .venv/lib/python*/...")
    return matches[0]


def grep_def(pkg: Path, name: str) -> list[str]:
    """Return matching `def name`/`class name` lines from the package."""
    # Match def/class definitions AND module-level singleton/constant assignments
    # (e.g. `Users = UsersTable()`, `KNOWLEDGE_BASES_COLLECTION = '...'`).
    n = re.escape(name)
    pattern = rf"((async def|def|class) {n}\b|^{n}\s*=)"
    try:
        out = subprocess.run(
            ["grep", "-rnE", pattern, str(pkg)],
            capture_output=True, text=True,
        ).stdout
    except FileNotFoundError:
        sys.exit("grep not available")
    return [l for l in out.splitlines() if l.strip()]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = Path(sys.argv[1])
    if not target.exists():
        sys.exit(f"No such file: {target}")
    src = target.read_text()
    pkg = find_pkg_root()

    # Imported symbols from open_webui.* (handles multi-line parenthesized imports).
    imported: set[str] = set()
    for m in re.finditer(r"from\s+open_webui[\w.]*\s+import\s+(\([^)]*\)|[^\n]+)", src):
        body = m.group(1).strip("() \n")
        for part in body.split(","):
            name = part.strip().split(" as ")[0].strip()
            if name and name != "*":
                imported.add(name)

    # Methods actually awaited: `await Something.method(`
    called: set[str] = set(re.findall(r"await\s+[A-Za-z_][\w.]*\.(\w+)\s*\(", src))

    print(f"=== {target} depends on (open_webui package at {pkg}) ===\n")

    print("-- imported symbols --")
    for name in sorted(imported):
        hits = grep_def(pkg, name)
        status = "FOUND" if hits else "MISSING !!!"
        print(f"[{status}] {name}")
        for h in hits[:3]:
            print(f"    {h}")

    print("\n-- awaited methods --")
    for name in sorted(called):
        hits = grep_def(pkg, name)
        status = "found" if hits else "MISSING !!!"
        print(f"[{status}] .{name}(")
        for h in hits[:3]:
            print(f"    {h}")


if __name__ == "__main__":
    main()
