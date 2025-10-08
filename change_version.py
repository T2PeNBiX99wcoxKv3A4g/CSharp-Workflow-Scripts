# coding: utf-8
import os

import typer
from icecream import ic


class OldVersionNotFound(Exception):
    def __init__(self, *args, **kwargs): pass


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


def string_handle(input_string: str, char_list: list[str]) -> str:
    ret_string = input_string
    for char in char_list:
        ret_string = ret_string.replace(char, "")
    return ret_string.strip()


class ChangeVersion(object):
    file_path: str
    find_keyword: str
    new_version: str
    old_version: str | None
    debug: bool
    split_keyword: str
    change_readme: bool
    readme_file_path: str
    extra_find_keyword_list: list[str]

    def __init__(self, file_path: str, find_keyword: str, new_version: str, debug: bool, split_keyword: str,
                 change_readme: bool, readme_file_path: str, extra_find_keywords: str):
        if debug:
            ic.enable()
        else:
            ic.disable()

        ic(file_path, find_keyword, new_version, split_keyword, change_readme, readme_file_path, extra_find_keywords)
        ic("Before", new_version)

        new_version = string_handle(new_version, remove_chars_in_new_version)

        if not new_version[0].isdigit():
            new_version = new_version[1:]

        ic("After", new_version)

        extra_find_keyword_list = extra_find_keywords.split(",")

        for i in range(len(extra_find_keyword_list)):
            extra_find_keyword_list[i] = extra_find_keyword_list[i].strip()
        ic(extra_find_keyword_list)

        self.file_path = file_path
        self.find_keyword = find_keyword
        self.new_version = new_version
        self.debug = debug
        self.split_keyword = split_keyword
        self.change_readme = change_readme
        self.readme_file_path = readme_file_path
        self.extra_find_keyword_list = extra_find_keyword_list

    def extra_find_keywords_check(self, line: str) -> bool:
        for extra_find_keyword in self.extra_find_keyword_list:
            if line.find(extra_find_keyword) < 0:
                return False
        return True

    @staticmethod
    def find_version_file() -> str | None:
        if not os.path.isfile(version_file):
            return None
        with open(version_file, "r") as file:
            get_version = file.readline().strip()
            file.close()
            return get_version

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
        old_version = self.find_version_file()
        if old_version is None:
            old_version = self.find_version_in_file()
        ic(old_version, self.new_version)
        if old_version is None:
            raise OldVersionNotFound(f'Old version is not found')
        self.old_version = old_version

    @staticmethod
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

    def create_version_file(self):
        with open(version_file, "w+") as file:
            file.write(self.new_version)
            file.close()

    def handle(self):
        self.find_version()

        typer.echo(f'Old version: {self.old_version}, New version: {self.new_version}')

        self.create_version_file()
        self.replace_keyword_in_file(self.file_path, self.old_version, self.new_version)

        if not self.change_readme:
            return

        self.replace_keyword_in_file(self.readme_file_path, self.old_version, self.new_version)


def main(file_path: str, find_keyword: str, new_version: str, debug: bool = False, split_keyword: str = "=",
         change_readme: bool = False, readme_file_path: str = "./README.md", extra_find_keywords: str = ""):
    ChangeVersion(file_path, find_keyword, new_version, debug, split_keyword, change_readme, readme_file_path,
                  extra_find_keywords).handle()


if __name__ == "__main__":
    typer.run(main)
