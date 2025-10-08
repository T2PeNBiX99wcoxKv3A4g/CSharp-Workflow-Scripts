# coding: utf-8
import os
import uuid
from enum import Enum

import typer
from icecream import ic


class InvalidVersionError(Exception):
    def __init__(self, *args, **kwargs): pass


class VersionType(Enum):
    OLD = 0
    NEW = 1


remove_chars_in_new_version = [
    "\"",
    "v"
]

remove_chars_in_version_path = [
    "\n",
    ";",
    "\"",
    ","
]

version_file = "./.version"
old_version_file = "./.version_old"
github_output_env_key = "GITHUB_OUTPUT"
app = typer.Typer()


def string_handle(input_string: str, char_list: list[str]) -> str:
    ret_string = input_string
    for char in char_list:
        ret_string = ret_string.replace(char, "")
    return ret_string.strip()


def find_version_file(version_file_path: str) -> str | None:
    if not os.path.isfile(version_file_path):
        return None
    with open(version_file_path, "r") as file:
        get_version = file.readline().strip()
        file.close()
        return get_version


def replace_keyword_in_file(file_path: str, old_string: str, new_string: str):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    ic(file_path, old_string, new_string)
    with open(file_path, "r+") as file:
        old_text = "".join(file.readlines())
        new_text = old_text.replace(old_string, new_string)
        ic(file_path, old_text, new_text)
        file.seek(0)
        file.truncate(0)
        file.write(new_text)
        file.close()


def write_version_file_in_path(new_version: str, version_file_path: str):
    with open(version_file_path, "w+") as file:
        file.write(new_version)
        file.close()
        typer.echo(f'write version ({new_version}) to {version_file_path}')


def write_version_file(new_version: str, version_file_type: VersionType):
    path = version_file if version_file_type == VersionType.NEW else old_version_file
    write_version_file_in_path(new_version, path)


def new_version_handle(new_version: str) -> str:
    output_string = new_version.split("-")
    ic(output_string)
    output_string[0] = string_handle(output_string[0], remove_chars_in_new_version)
    ic(output_string)
    if not output_string[0][0].isdigit():
        raise InvalidVersionError(f'Invalid version: {new_version}')
    return "-".join(output_string)


def extra_find_keywords_handle(extra_find_keywords: str) -> list[str]:
    extra_find_keywords_list = extra_find_keywords.split(",")
    for i in range(len(extra_find_keywords_list)):
        extra_find_keywords_list[i] = extra_find_keywords_list[i].strip()
    return extra_find_keywords_list


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
    with open(os.environ[github_output_env_key], "a") as fh:
        typer.echo(f"{name}={value}", file=fh)


# refs: https://github.com/orgs/community/discussions/28146
def github_multiline_output(name: str, value: str):
    if github_output_env_key not in os.environ:
        typer.echo(f"[{github_output_env_key}] environment variable is not set.")
        return
    with open(os.environ[github_output_env_key], "a") as fh:
        delimiter = uuid.uuid1()
        typer.echo(f'{name}<<{delimiter}', file=fh)
        typer.echo(value, file=fh)
        typer.echo(delimiter, file=fh)


class ChangeVersion(object):
    file_path: str
    find_keyword: str
    new_version: str
    old_version: str | None
    split_keyword: str
    extra_find_keyword_list: list[str]
    only_replace: bool

    def __init__(self, file_path: str, find_keyword: str, new_version: str, split_keyword: str,
                 extra_find_keywords: str, only_replace: bool):
        ic(file_path, find_keyword, new_version, split_keyword, extra_find_keywords)
        self.file_path = file_path
        self.find_keyword = find_keyword
        self.new_version = ic(new_version_handle(new_version))
        self.split_keyword = split_keyword
        self.extra_find_keyword_list = ic(extra_find_keywords_handle(extra_find_keywords))
        self.only_replace = only_replace

    def extra_find_keywords_check(self, line: str) -> bool:
        for extra_find_keyword in self.extra_find_keyword_list:
            if line.find(extra_find_keyword) < 0:
                return False
        return True

    def find_version_in_file(self) -> str | None:
        found_version: str | None = None

        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(self.file_path)

        with open(self.file_path, "r+") as file:
            for line in file.readlines():
                start = line.find(self.find_keyword)

                ic(line, start)

                if start < 0:
                    continue

                if start != 0 and line[start - 1] != ' ':
                    continue

                if len(self.extra_find_keyword_list) > 0 and not self.extra_find_keywords_check(line):
                    continue

                version_paths = line.split(self.split_keyword)

                if len(version_paths) < 2:
                    continue

                ic(version_paths)
                found_version = string_handle(version_paths[1], remove_chars_in_version_path)
            file.close()
            return found_version

    def find_version(self):
        old_version = find_version_file(version_file)

        if old_version == self.new_version and not self.only_replace:
            typer.echo(f'Old version inside .version is same as new version: {old_version}')
            self.only_replace = True
        if self.only_replace:
            old_version = None
        if old_version is None:
            old_version = self.find_version_in_file()
        ic(old_version, self.new_version)
        if old_version is None:
            raise InvalidVersionError(f'Old version is not found')
        self.old_version = old_version

    def handle(self):
        self.find_version()

        typer.echo(f'Old version: {self.old_version}, New version: {self.new_version}')

        replace_keyword_in_file(self.file_path, self.old_version, self.new_version)

        if self.only_replace:
            return

        write_version_file(self.new_version, VersionType.NEW)
        write_version_file(self.old_version, VersionType.OLD)
        github_output("old_version", self.old_version)
        github_output("new_version", self.new_version)


@app.command()
def change_version(file_path: str, find_keyword: str, new_version: str, split_keyword: str = "=",
                   extra_find_keywords: str = "", only_replace: bool = False, debug: bool = False):
    debug_output_control(debug)
    ChangeVersion(file_path, find_keyword, new_version, split_keyword, extra_find_keywords, only_replace).handle()


@app.command()
def create_version_file(new_version: str, debug: bool = False):
    debug_output_control(debug)
    handle_new_version = ic(new_version_handle(new_version))
    write_version_file(handle_new_version, VersionType.NEW)
    github_output("new_version", handle_new_version)


@app.command()
def replace_version(file_path: str, debug: bool = False):
    debug_output_control(debug)
    old_version = find_version_file(old_version_file)
    if old_version is None:
        raise InvalidVersionError(f'Old version is not found in .version_old')
    new_version = find_version_file(version_file)
    if new_version is None:
        raise InvalidVersionError(f'New version is not found in .version')
    replace_keyword_in_file(file_path, old_version, new_version)


if __name__ == "__main__":
    app()
