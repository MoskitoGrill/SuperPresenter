"""Read-only song checks. Run directly; no GUI or third-party packages needed."""

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from superpresenter.services.construct_parser import parse_construct, ConstructError, RepeatGroup
from superpresenter.services.stationary_pages import presentation_lines


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
    # Historical diagnostics stay unchanged; marked guides are checked also
    # at the legacy variant-local location.
    for repetition in root.iter('repetition'):
        if '@' not in (repetition.text or ''):
            continue
        expression = ' '.join(line.strip() for line in (repetition.text or '').split('\n')
                              if line.strip())
        targets = [v for v in variants if repetition in list(v)] or variants
        for variant in targets:
            rows = {s.get('name', ''): presentation_lines((s.text or '').split('\n'))
                    for s in variant.findall('section')}
            try:
                if len(repetition):
                    raise ValueError('Nested elements are not supported in a marked repetition')
                pending = list(parse_construct(expression, rows).instructions)
                while pending:
                    node = pending.pop()
                    if isinstance(node, RepeatGroup):
                        pending.extend(node.children)
                    elif node.pinned and (node.end_line or node.start_line) > len(rows[node.section]):
                        raise ValueError(f'Pinned selection exceeds section {node.section!r}')
            except (ConstructError, ValueError) as exc:
                report('error', 'repetition_pin', f"variant {variant.get('name', '')}: {exc}")
    if not repetitions:
        report("warning", "repetition_missing", "No repetition found.")
    existing = set().union(*section_sets)
    for index, repetition in enumerate(repetitions, 1):
        expression = (repetition.text or "").strip()
        label = f"repetition {index} ({repetition.get('name', '')})"
        if '@' in expression:
            continue
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
