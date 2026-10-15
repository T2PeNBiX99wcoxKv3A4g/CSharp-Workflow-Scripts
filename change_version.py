# coding: utf-8
import os
import re
from enum import Enum

import typer
from icecream import ic


class InvalidVersionError(Exception):
    pass


class VersionFileType(Enum):
    OLD = 0
    NEW = 1


# Characters stripped from the version passed on the command line and from the
# version detected inside a file.
strip_chars_from_new_version = ["\"", "v"]
strip_chars_from_detected_version = ["\n", ";", "\"", ","]

# Lines starting with one of these are comments in the formats we support
# (properties/ini/toml/yaml use "#", "!" or ";", C#/XML use "//" or "<!--").
comment_line_prefixes = ("#", "!", "//", "<!--", ";")

# version_key is an exact key name, not a fuzzy search fragment, so the pattern
# built from it is case-sensitive and anchored to token boundaries. That keeps
# "Version" from matching "AssemblyVersion" or "<SupportedOSPlatformVersion>".
key_start_boundary = r'(?<![0-9A-Za-z_.\-])'
key_end_boundary = r'(?![0-9A-Za-z_\-])'
key_value_separators = "=:>("
version_value_pattern = r'["\']?(?P<version>[0-9vV][^"\'\s<>#;,]*)'

# .version holds the version produced by the current run, .version_old holds the
# version that was replaced by it.
new_version_file = "./.version"
old_version_file = "./.version_old"

github_output_env_key = "GITHUB_OUTPUT"
github_output_warning_shown = False
app = typer.Typer()


def strip_chars(input_string: str, chars: list[str]) -> str:
    result = input_string
    for char in chars:
        result = result.replace(char, "")
    return result.strip()


def read_version_file(file_path: str) -> str | None:
    if not os.path.isfile(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as file:
        version = file.readline().strip()
    return version or None


def write_version_to_file(version: str, file_path: str):
    with open(file_path, "w+", encoding="utf-8") as file:
        file.write(version)
        typer.echo(f'Wrote version {version} to {file_path}.')


def write_version_file(version: str, file_type: VersionFileType):
    file_path = new_version_file if file_type == VersionFileType.NEW else old_version_file
    write_version_to_file(version, file_path)


def echo_replacement(file_path: str, old_version: str, new_version: str, count: int, unit: str):
    unit_label = unit if count == 1 else f'{unit}s'
    typer.echo(f'Replaced version {old_version} with {new_version} in {file_path}, updating {count} {unit_label}.')


def normalize_version(new_version: str) -> str:
    parts = new_version.split("-")
    ic(parts)
    parts[0] = strip_chars(parts[0], strip_chars_from_new_version)
    ic(parts)
    if not parts[0] or not parts[0][0].isdigit():
        raise InvalidVersionError(f'Invalid version "{new_version}": a version must start with a digit.')
    return "-".join(parts)


def parse_require_keywords(require_keywords: str) -> list[str]:
    return [keyword.strip() for keyword in require_keywords.split(",") if keyword.strip()]


def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith(comment_line_prefixes)


def build_version_pattern(version_key: str) -> re.Pattern[str]:
    if not version_key:
        raise InvalidVersionError('The version key must not be empty.')

    # A key that already carries the value delimiter (e.g. "<Version>") does not
    # need a second separator, every other key must be followed by one. The
    # optional quote covers quoted keys such as JSON's `"Version": "0.1.0"`.
    if version_key.endswith(">"):
        separator = r'\s*'
    else:
        separator = rf'\s*["\']?\s*[{re.escape(key_value_separators)}]+\s*'

    end_boundary = key_end_boundary if re.search(r'[0-9A-Za-z_]$', version_key) else ''

    return re.compile(
        key_start_boundary
        + re.escape(version_key)
        + end_boundary
        + separator
        + version_value_pattern
    )


def extract_version(match: re.Match[str]) -> str:
    return strip_chars(match.group("version"), strip_chars_from_detected_version)


def match_target_line(line: str, version_pattern: re.Pattern[str],
                      required_keywords: list[str]) -> re.Match[str] | None:
    if is_comment_line(line):
        return None
    if not all(keyword in line for keyword in required_keywords):
        return None
    return version_pattern.search(line)


def find_version_in_line(line: str, version_pattern: re.Pattern[str],
                         required_keywords: list[str]) -> str | None:
    match = match_target_line(line, version_pattern, required_keywords)
    if match is None:
        return None
    return extract_version(match)


def replace_version_in_match(match: re.Match[str], old_version: str, new_version: str) -> str:
    # Leave the match alone when it holds a different version, so a matching key
    # sitting next to an unrelated version is never rewritten.
    if extract_version(match) != old_version:
        return match.group(0)
    matched_text = match.group(0)
    version_start = match.start("version") - match.start()
    version_end = match.end("version") - match.start()
    return matched_text[:version_start] + new_version + matched_text[version_end:]


def replace_version_in_target_lines(file_path: str, version_pattern: re.Pattern[str],
                                    required_keywords: list[str], old_version: str,
                                    new_version: str) -> int:
    """Replace old_version on every line whose version_key matches.

    Only the version inside the match is rewritten, and only when it is the
    version being replaced. Lines without the key keep their content, so a
    version that merely appears as a substring of an unrelated value is left
    alone. Returns the number of lines that changed.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f'File not found: {file_path}.')

    def replace_match(match: re.Match[str]) -> str:
        return replace_version_in_match(match, old_version, new_version)

    # newline="" keeps the original line endings, so CRLF files stay CRLF even
    # when this runs on Linux.
    with open(file_path, "r+", encoding="utf-8", newline="") as file:
        lines = file.readlines()
        replaced_lines = [
            version_pattern.sub(replace_match, line)
            if match_target_line(line, version_pattern, required_keywords) is not None
            else line
            for line in lines
        ]
        changed_line_count = sum(1 for line, replaced_line in zip(lines, replaced_lines) if line != replaced_line)
        ic(file_path, changed_line_count)
        if changed_line_count > 0:
            file.seek(0)
            file.truncate(0)
            file.write("".join(replaced_lines))
        return changed_line_count


def replace_version_in_file(file_path: str, old_version: str, new_version: str) -> int:
    """Replace every occurrence of old_version in the file, key or no key.

    Returns how many occurrences were replaced.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f'File not found: {file_path}.')

    ic(file_path, old_version, new_version)
    # newline="" keeps the original line endings, so CRLF files stay CRLF even
    # when this runs on Linux.
    with open(file_path, "r+", encoding="utf-8", newline="") as file:
        old_text = file.read()
        replaced_count = old_text.count(old_version)
        if replaced_count == 0:
            return 0
        new_text = old_text.replace(old_version, new_version)
        ic(file_path, old_text, new_text)
        file.seek(0)
        file.truncate(0)
        file.write(new_text)
        return replaced_count


def debug_output_control(debug: bool):
    if debug:
        ic.enable()
    else:
        ic.disable()


# refs: https://github.com/orgs/community/discussions/28146
def github_output(name: str, value: str):
    global github_output_warning_shown

    if github_output_env_key not in os.environ:
        if not github_output_warning_shown:
            typer.echo(f'The {github_output_env_key} environment variable is not set,'
                       f' so the workflow outputs were skipped.')
            github_output_warning_shown = True
        return
    with open(os.environ[github_output_env_key], "a", encoding="utf-8") as fh:
        typer.echo(f"{name}={value}", file=fh)


class ChangeVersion:
    file_path: str
    version_key: str
    new_version: str
    old_version: str
    required_keywords: list[str]
    version_pattern: re.Pattern[str]

    def __init__(self, file_path: str, version_key: str, new_version: str, require_keywords: str = ""):
        ic(file_path, version_key, new_version, require_keywords)
        self.file_path = file_path
        self.version_key = version_key
        self.new_version = ic(normalize_version(new_version))
        self.required_keywords = ic(parse_require_keywords(require_keywords))
        self.version_pattern = ic(build_version_pattern(version_key))

    def detect_old_version(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f'File not found: {self.file_path}.')

        detected_version: str | None = None
        with open(self.file_path, "r", encoding="utf-8", newline="") as file:
            for line in file:
                detected_version = find_version_in_line(line, self.version_pattern, self.required_keywords)
                if detected_version is not None:
                    break

        ic(detected_version, self.new_version)
        if detected_version is None:
            raise InvalidVersionError(f'No version was found for key "{self.version_key}" in {self.file_path}.')
        self.old_version = detected_version

    def run(self):
        self.detect_old_version()

        changed_line_count = replace_version_in_target_lines(
            self.file_path, self.version_pattern, self.required_keywords, self.old_version, self.new_version)
        if changed_line_count == 0:
            # detect_old_version already proved a matching line exists, so a zero
            # count means that line already carries new_version. Fail before any
            # state is written, a wrong bump is worse than a failed one.
            raise InvalidVersionError(f'No version was replaced in {self.file_path}.'
                                      f' It already holds version {self.new_version}.')

        echo_replacement(self.file_path, self.old_version, self.new_version, changed_line_count, 'line')

        write_version_file(self.new_version, VersionFileType.NEW)
        write_version_file(self.old_version, VersionFileType.OLD)
        github_output("old_version", self.old_version)
        github_output("new_version", self.new_version)


@app.command()
def change_version(file_path: str, version_key: str, new_version: str,
                   require_keywords: str = "", debug: bool = False):
    debug_output_control(debug)
    ChangeVersion(file_path, version_key, new_version, require_keywords).run()


@app.command()
def create_version_file(new_version: str, debug: bool = False):
    debug_output_control(debug)
    normalized_version = ic(normalize_version(new_version))
    write_version_file(normalized_version, VersionFileType.NEW)
    github_output("new_version", normalized_version)


@app.command()
def replace_version(file_path: str, version_key: str = "", debug: bool = False):
    debug_output_control(debug)
    old_version = read_version_file(old_version_file)
    if old_version is None:
        raise InvalidVersionError(f'No version was found in {old_version_file}. Run change-version first.')
    new_version = read_version_file(new_version_file)
    if new_version is None:
        raise InvalidVersionError(f'No version was found in {new_version_file}.'
                                  f' Run change-version or create-version-file first.')

    # Without --version-key every occurrence is replaced, which is what
    # documentation files such as README.md need.
    if not version_key:
        replaced_count = replace_version_in_file(file_path, old_version, new_version)
        if replaced_count == 0:
            typer.echo(f'Version {old_version} was not found in {file_path}, so nothing was replaced.')
            return
        echo_replacement(file_path, old_version, new_version, replaced_count, 'occurrence')
        return

    version_pattern = ic(build_version_pattern(version_key))
    changed_line_count = replace_version_in_target_lines(file_path, version_pattern, [], old_version, new_version)
    if changed_line_count == 0:
        raise InvalidVersionError(f'No line in {file_path} matches the key "{version_key}".')
    echo_replacement(file_path, old_version, new_version, changed_line_count, 'line')


if __name__ == "__main__":
    app()
