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


def string_handle(input_string: str, char_list: list[str]) -> str:
    ret_string = input_string
    for char in char_list:
        ret_string = ret_string.replace(char, "")
    return ret_string.strip()


def extra_find_keywords_check(extra_find_keyword_list: list[str], line: str) -> bool:
    for extra_find_keyword in extra_find_keyword_list:
        if line.find(extra_find_keyword) < 0:
            return False
    return True


def main(file_path: str, find_keyword: str, new_version: str, debug: bool = False, split_keyword: str = "=",
         change_readme: bool = False, readme_file_path: str = "./README.md", extra_find_keywords: str = ""):
    if debug:
        ic.enable()
    else:
        ic.disable()

    ic(file_path, find_keyword, new_version, split_keyword, change_readme, readme_file_path, extra_find_keywords)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    ic(new_version)

    new_version = string_handle(new_version, remove_chars_in_new_version)
    extra_find_keyword_list = extra_find_keywords.split(",")

    for i in range(len(extra_find_keyword_list)):
        extra_find_keyword_list[i] = extra_find_keyword_list[i].strip()
    ic(extra_find_keyword_list)

    if not new_version[0].isdigit():
        new_version = new_version[1:]

    ic(new_version)

    old_version: str = ""

    with open(file_path, "r+") as file:
        old_text = ""

        for line in file.readlines():
            start = line.find(find_keyword)

            ic(line, start)

            if start < 0:
                old_text += line
                continue

            if start != 0 and line[start - 1] != ' ':
                old_text += line
                continue

            if len(extra_find_keyword_list) > 0 and not extra_find_keywords_check(extra_find_keyword_list, line):
                old_text += line
                continue

            version_paths = line.split(split_keyword)

            if len(version_paths) < 2:
                old_text += line
                continue

            ic(version_paths)

            old_version = string_handle(version_paths[1], remove_chars_in_version_path)
            typer.echo(f'Old version: {old_version}, New version: {new_version}')
            old_text += line

        ic(old_version, new_version)
        if old_version == "":
            raise OldVersionNotFound(f'Old version is not found')

        new_text = old_text.replace(old_version, new_version)
        file.seek(0)
        file.truncate(0)
        file.write(new_text)
        file.close()

    if not change_readme:
        return

    if not os.path.isfile(readme_file_path):
        raise FileNotFoundError(readme_file_path)

    with open(readme_file_path, "r+") as file:
        old_text = "".join(file.readlines())
        new_text = old_text.replace(old_version, new_version)
        ic(old_text, new_text)
        file.seek(0)
        file.truncate(0)
        file.write(new_text)
        file.close()


if __name__ == "__main__":
    typer.run(main)
