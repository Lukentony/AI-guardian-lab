"""One conservative shell parser for validation, intent and forensic annotation.

This is deliberately NOT a complete Bash interpreter. Unsupported syntax is denied
before execution; normalization is never used as a substitute for shell semantics.
Parser-specific errors are normalized to the same explicit denial boundary.
"""

import os
from dataclasses import dataclass

import bashlex
from bashlex.errors import ParsingError


class UnsupportedShellError(ValueError):
    pass


@dataclass(frozen=True)
class ShellCommand:
    executable: str
    arguments: tuple[str, ...]
    redirects: tuple[tuple[str, str], ...]

    @property
    def binary(self):
        return os.path.basename(self.executable)

    @property
    def trusted_executable(self):
        # A basename match must not authorize an attacker-controlled /tmp/ls.
        return "/" not in self.executable or self.executable in {
            f"/bin/{self.binary}",
            f"/usr/bin/{self.binary}",
        }


def parse_commands(command: str) -> list[ShellCommand]:
    if not isinstance(command, str) or not command.strip() or "\x00" in command:
        raise UnsupportedShellError("A non-empty shell command is required")
    # Newlines, comments, globs and expansions complicate execution semantics.
    # Ordinary quoted strings remain supported; expansion nodes are rejected below.
    if "\n" in command or "\r" in command:
        raise UnsupportedShellError("Multiline shell commands are not supported")
    try:
        trees = bashlex.parse(command)
    except (ValueError, NotImplementedError, ParsingError) as exc:
        raise UnsupportedShellError("Unsupported or malformed shell syntax") from exc
    result = []

    def visit(node):
        if node.kind in {"list", "pipeline"}:
            for part in node.parts:
                if part.kind == "operator":
                    if part.op not in {";", "&&", "||"}:
                        raise UnsupportedShellError(
                            "Background/control operators are not supported"
                        )
                elif part.kind == "pipe":
                    if part.pipe != "|":
                        raise UnsupportedShellError("Unsupported pipeline")
                else:
                    visit(part)
        elif node.kind == "command":
            words, redirects = [], []
            for part in node.parts:
                if part.kind == "word":
                    if part.parts:
                        raise UnsupportedShellError("Shell expansions are not supported")
                    # bashlex leaves globbing to the shell: deny it rather than
                    # overlooking filenames/arguments introduced at execution time.
                    if any(c in command[part.pos[0] : part.pos[1]] for c in "*?["):
                        raise UnsupportedShellError("Shell globbing is not supported")
                    words.append(part.word)
                elif part.kind == "redirect":
                    if part.type not in {"<", ">", ">>"} or not hasattr(part.output, "word"):
                        raise UnsupportedShellError("Unsupported redirection")
                    if part.output.parts:
                        raise UnsupportedShellError("Redirection expansion is not supported")
                    redirects.append((part.type, part.output.word))
                else:
                    # Includes assignments (PATH/LD_PRELOAD), compound commands,
                    # substitutions, process substitutions and shell wrappers.
                    raise UnsupportedShellError(
                        "Assignments and compound shell syntax are not supported"
                    )
            if not words:
                raise UnsupportedShellError("Redirection-only commands are not supported")
            result.append(ShellCommand(words[0], tuple(words[1:]), tuple(redirects)))
        else:
            raise UnsupportedShellError(f"Unsupported shell construct: {node.kind}")

    for tree in trees:
        visit(tree)
    if not result:
        raise UnsupportedShellError("No executable command found")
    return result


def extract_binaries(command: str) -> list[str]:
    return [part.binary for part in parse_commands(command)]
