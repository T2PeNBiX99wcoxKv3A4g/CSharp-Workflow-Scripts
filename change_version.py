# coding: utf-8
import os
import typer

from icecream import ic


class OldVersionNotFound(Exception):
    def __init__(self, *args, **kwargs): pass


def main(file_path: str, find_keyword: str, new_version: str, debug: bool = False):
    if debug:
        ic.enable()
    else:
        ic.disable()

    ic(file_path, find_keyword, new_version)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    ic(new_version)

    new_version = new_version.replace('"', '').replace("v", "")

    if not new_version[0].isdigit():
        new_version = new_version[1:]

    ic(new_version)

    old_version: str = ""

    with open(file_path, "r+") as file:
        old_text = ""

        for line in file.readlines():
            start = line.find(find_keyword)

            ic(line)

            if start < 0:
                old_text += line
                continue

            version_paths = line.split("=")

            if len(version_paths) < 1:
                old_text += line
                continue

            if line.find("string") < 0:
                old_text += line
                continue

            ic()

            old_version = version_paths[1].replace("\n", "").replace(";", "").replace("\"", "").strip()
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


if __name__ == "__main__":
    typer.run(main)
