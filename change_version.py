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
        return file.readline().strip()


def write_version_to_file(version: str, file_path: str):
    with open(file_path, "w+", encoding="utf-8") as file:
        file.write(version)
        typer.echo(f'write version ({version}) to {file_path}')


def write_version_file(version: str, file_type: VersionFileType):
    file_path = new_version_file if file_type == VersionFileType.NEW else old_version_file
    write_version_to_file(version, file_path)


def normalize_version(new_version: str) -> str:
    parts = new_version.split("-")
    ic(parts)
    parts[0] = strip_chars(parts[0], strip_chars_from_new_version)
    ic(parts)
    if not parts[0] or not parts[0][0].isdigit():
        raise InvalidVersionError(f'Invalid version: {new_version}')
    return "-".join(parts)


def parse_require_keywords(require_keywords: str) -> list[str]:
    return [keyword.strip() for keyword in require_keywords.split(",") if keyword.strip()]


def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith(comment_line_prefixes)


def build_version_pattern(version_key: str) -> re.Pattern[str]:
    if not version_key:
        raise InvalidVersionError('version_key must not be empty')

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
    return match.group("version")


def debug_output_control(debug: bool):
    if debug:
        ic.enable()
    else:
        ic.disable()


# refs: https://github.com/orgs/community/discussions/28146
def github_output(name: str, value: str):
    if github_output_env_key not in os.environ:
        typer.echo(f"[{github_output_env_key}] environment variable is not set.")
        return
    with open(os.environ[github_output_env_key], "a", encoding="utf-8") as fh:
        typer.echo(f"{name}={value}", file=fh)


def replace_version_in_file(file_path: str, old_version: str | None, new_version: str):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    ic(file_path, old_version, new_version)
    if old_version is None:
        typer.echo(f'Old version is unknown, skip replace in {file_path}')
        return
    # newline="" keeps the original line endings, so CRLF files stay CRLF even
    # when this runs on Linux.
    with open(file_path, "r+", encoding="utf-8", newline="") as file:
        old_text = file.read()
        new_text = old_text.replace(old_version, new_version)
        ic(file_path, old_text, new_text)
        file.seek(0)
        file.truncate(0)
        file.write(new_text)


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

    def required_keywords_present(self, line: str) -> bool:
        return all(keyword in line for keyword in self.required_keywords)

    def detect_version_in_line(self, line: str) -> str | None:
        match = self.version_pattern.search(line)
        if match is None:
            return None
        return strip_chars(extract_version(match), strip_chars_from_detected_version)

    def detect_version_in_file(self) -> str | None:
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(self.file_path)

        with open(self.file_path, "r", encoding="utf-8", newline="") as file:
            for line in file:
                if is_comment_line(line):
                    continue
                if not self.required_keywords_present(line):
                    continue
                detected_version = self.detect_version_in_line(line)
                if detected_version is not None:
                    ic(detected_version)
                    return detected_version
        return None

    def detect_old_version(self):
        detected_version = self.detect_version_in_file()
        ic(detected_version, self.new_version)
        if detected_version is None:
            raise InvalidVersionError(f'Old version is not found in {self.file_path}')
        self.old_version = detected_version

    def run(self):
        self.detect_old_version()

        typer.echo(f'Old version: {self.old_version}, New version: {self.new_version}')

        replace_version_in_file(self.file_path, self.old_version, self.new_version)
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
def replace_version(file_path: str, debug: bool = False):
    debug_output_control(debug)
    old_version = read_version_file(old_version_file)
    if old_version is None:
        raise InvalidVersionError('Old version is not found in .version_old')
    new_version = read_version_file(new_version_file)
    if new_version is None:
        raise InvalidVersionError('New version is not found in .version')
    replace_version_in_file(file_path, old_version, new_version)


if __name__ == "__main__":
    app()
