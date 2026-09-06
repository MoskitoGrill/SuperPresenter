"""Read-only song checks. Run directly; no GUI or third-party packages needed."""

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


# Preserve legacy IDs (r, r0, v1a), rather than imposing editor numbering.
SECTION_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*", re.ASCII)


@dataclass(frozen=True)
class Issue:
    path: Path
    severity: str
    code: str
    message: str


def validate_song(path: Path) -> list[Issue]:
    """Validate one file without modifying it; unknown repetition syntax is skipped."""
    path = Path(path)
    issues = []

    def report(severity, code, message):
        issues.append(Issue(path, severity, code, message))

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError, ValueError, LookupError) as exc:
        report("error", "xml", str(exc))
        return issues
    if root.tag != "slide":
        report("error", "root", "Root element must be slide.")
    if not root.get("name", "").strip():
        report("error", "title", "Song name is empty or missing.")
    variants = root.findall("variant")
    if not variants:
        report("error", "variant_missing", "No variant found.")
    section_sets = []
    for index, variant in enumerate(variants, 1):
        label = f"variant {index} ({variant.get('name', '')})"
        if not variant.get("name", "").strip():
            report("error", "variant_name", f"{label}: missing name.")
        identifiers = set()
        if not variant.findall("section"):
            report("error", "section_missing", f"{label}: no sections.")
        for section in variant.findall("section"):
            sid = section.get("name", "")
            if not SECTION_ID.fullmatch(sid):
                report("error", "section_id", f"{label}: invalid section ID {sid!r}.")
            if sid in identifiers:
                report("error", "section_duplicate", f"{label}: duplicate ID {sid!r}.")
            identifiers.add(sid)
            if not (section.text or "").strip():
                report("error", "section_text", f"{label}: section {sid!r} has no text.")
        section_sets.append(identifiers)
    repetitions = root.findall("repetition")
    if not repetitions:
        report("warning", "repetition_missing", "No repetition found.")
    existing = set().union(*section_sets)
    for index, repetition in enumerate(repetitions, 1):
        expression = (repetition.text or "").strip()
        label = f"repetition {index} ({repetition.get('name', '')})"
        if not expression:
            report("warning", "repetition_empty", f"{label}: empty expression.")
            continue
        tokens = expression.split()
        # Only a complete whitespace-separated list is interpreted. No eval,
        # partial token extraction, expansion, or changes to application parsers.
        if len(repetition) or not all(SECTION_ID.fullmatch(t) for t in tokens):
            report("warning", "repetition_unchecked", f"{label}: unsupported expression {expression!r}.")
            continue
        for sid in sorted(set(tokens)):
            if sid not in existing:
                report("error", "repetition_reference", f"{label}: unknown section {sid!r}.")
            elif any(sid not in ids for ids in section_sets):
                report("warning", "repetition_variant", f"{label}: section {sid!r} is missing in some variants.")
    return issues


def validate_directory(directory: Path) -> tuple[list[Path], list[Issue]]:
    """Return deterministically ordered files and diagnostics, including subfolders."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    files = sorted(directory.rglob("*.xml"))
    if not files:
        raise ValueError(f"No XML files found: {directory}")
    return files, [issue for path in files for issue in validate_song(path)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "songs")
    parser.add_argument("--details", action="store_true", help="Print every diagnostic.")
    args = parser.parse_args(argv)
    try:
        files, issues = validate_directory(args.directory)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    counts = Counter(issue.severity for issue in issues)
    print(f"Files: {len(files)}; errors: {counts['error']}; warnings: {counts['warning']}")
    for (severity, code), count in sorted(Counter((i.severity, i.code) for i in issues).items()):
        print(f"  {severity}: {code}: {count}")
    if args.details:
        for issue in issues:
            print(f"{issue.path}: {issue.severity} [{issue.code}] {issue.message}")
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    # Older Windows consoles cannot encode all song names/languages.
    sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
