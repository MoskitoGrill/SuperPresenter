"""Construct grammar, independent of UI, song text and projection styles.

Positions are zero-based offsets into the original input. Groups retain their
identity: legacy short-text navigation reuses group lines on every iteration.
See docs/construct_syntax.md for intentional historical edge cases.
"""
from dataclasses import dataclass
from typing import Iterable, Union


class ConstructError(ValueError):
    def __init__(self, message: str, position: int):
        self.position = position
        super().__init__(f'{message} (pozice {position}, počítáno od 0)')


class ParenthesisError(ConstructError):
    pass


class UnknownSectionError(ConstructError):
    pass


class InvalidRangeError(ConstructError):
    pass


class ExpectedNumberError(ConstructError):
    pass


class EmptyConstructError(ConstructError):
    pass


@dataclass(frozen=True)
class SectionStep:
    section: str
    position: int
    # Inclusive, historically one-based (zero is preserved for compatibility).
    start_line: int | None = None
    end_line: int | None = None


@dataclass(frozen=True)
class RepeatGroup:
    children: tuple['Instruction', ...]
    repeat: int
    position: int
    # This boundary is needed to reuse/pin lines in legacy short-text output.
    reuse_lines: bool = True


Instruction = Union[SectionStep, RepeatGroup]


@dataclass(frozen=True)
class Construct:
    instructions: tuple[Instruction, ...]

    def to_legacy(self) -> tuple[list, list[str]]:
        """Compile to the existing stack program without expanding repetitions.

        Section indices follow first textual occurrence; sibling instructions
        are emitted backwards because the renderer pops them off a stack.
        """
        used: list[str] = []

        pending = list(reversed(self.instructions))
        while pending:
            node = pending.pop()
            if isinstance(node, RepeatGroup):
                pending.extend(reversed(node.children))
            elif node.section not in used:
                used.append(node.section)
        indices = {section: index for index, section in enumerate(used)}
        program = []
        pending = [[len(self.instructions), 'conn'], *self.instructions]
        while pending:
            node = pending.pop()
            if isinstance(node, list):
                program.extend(node)
            elif isinstance(node, RepeatGroup):
                pending.append([len(node.children), 'conn', node.repeat, 'mult'])
                pending.extend(node.children)
            else:
                program.append(indices[node.section])
                if node.start_line is None:
                    program.append('all')
                elif node.end_line is None:
                    program.extend([node.start_line, 'line'])
                else:
                    program.extend([node.start_line, node.end_line, 'lins'])
        return program, used


def parse_construct(text: str, available_sections: Iterable[str]) -> Construct:
    """Parse a construct into immutable, ordered section/group instructions.

    Only ASCII space is a separator, as in WidgetSource. Line count validation
    is impossible with section names alone. No repetition is eagerly expanded.
    """
    legal = set(available_sections)
    # Explicit stack avoids recursion limits for nested input during parsing.
    frames: list[tuple[list[Instruction], int]] = [([], 0)]
    pos = 0

    def spaces():
        nonlocal pos
        while pos < len(text) and text[pos] == ' ':
            pos += 1

    def number(operator):
        nonlocal pos
        spaces()
        start = pos
        while pos < len(text) and '0' <= text[pos] <= '9':
            pos += 1
        if pos == start:
            raise ExpectedNumberError(f'Očekávané číslo za "{operator}"', start)
        try:
            return int(text[start:pos])
        except ValueError as exc:
            raise ExpectedNumberError('Číslo je příliš dlouhé', start) from exc

    while pos < len(text):
        char = text[pos]
        if char == ' ':
            pos += 1
        elif char == '(':
            frames.append(([], pos))
            pos += 1
        elif char == ')':
            if len(frames) == 1:
                raise ParenthesisError('Uzavírací závorka nemá odpovídající otevírací závorku', pos)
            children, start = frames.pop()
            pos += 1
            repeat = 2
            spaces()
            if pos < len(text) and text[pos] == '*':
                pos += 1
                repeat = number('*')
            frames[-1][0].append(RepeatGroup(tuple(children), repeat, start))
        else:
            start = pos
            while pos < len(text) and text[pos] not in ' .()':
                pos += 1
            section = text[start:pos]
            if section not in legal:
                raise UnknownSectionError(f'Neznámá sekce "{section}"', start)
            first = last = None
            spaces()
            if pos < len(text) and text[pos] == '.':
                pos += 1
                first = number('.')
                spaces()
                if pos < len(text) and text[pos] == ':':
                    pos += 1
                    spaces()
                    range_position = pos
                    last = number(':')
                    if last <= first:
                        raise InvalidRangeError('Konec rozsahu musí být větší než začátek', range_position)
            frames[-1][0].append(SectionStep(section, start, first, last))
    if len(frames) > 1:
        raise ParenthesisError('Neuzavřená závorka', frames[-1][1])
    if not frames[0][0]:
        raise EmptyConstructError('Construct (opakování) je prázdný', 0)
    return Construct(tuple(frames[0][0]))
