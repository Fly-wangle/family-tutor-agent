#!/usr/bin/env python3
"""Check publishable files for known privacy markers and broken local links."""

from pathlib import Path
import re
import subprocess
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DENY_PATTERNS = (
    r"/U[s]ers/", r"[A-Z]:\\U[s]ers\\",
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}",
)
LINK = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)")
SAFE_BINARY = {"assets/family-tutor-agent-hero.png"}


def check_files(root: Path, paths: list[str]) -> list[str]:
    errors = []
    for relative in paths:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            errors.append(f"{relative}: missing file or symlink")
            continue
        if relative in SAFE_BINARY:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            errors.append(f"{relative}: unexpected binary file")
            continue
        for pattern in DENY_PATTERNS:
            if re.search(pattern, content, flags=re.IGNORECASE):
                # Do not echo the matched private value into logs.
                errors.append(f"{relative}: known privacy marker")
                break
        if path.suffix == ".md":
            for match in LINK.finditer(content):
                link = match.group(1) or match.group(2)
                if link.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                link_path = unquote(link.split("#", 1)[0])
                destination = (path.parent / link_path).resolve()
                if not destination.is_relative_to(root.resolve()) or not destination.exists():
                    errors.append(f"{relative}: broken or external local link")
    return errors


def main() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    paths = sorted(set(item for item in result.stdout.decode().split("\0") if item))
    errors = check_files(ROOT, paths)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"Checked {len(paths)} publishable files: no known privacy markers or broken local links.")
    print("This is a limited check, not a substitute for staged-diff and history review.")


if __name__ == "__main__":
    main()
