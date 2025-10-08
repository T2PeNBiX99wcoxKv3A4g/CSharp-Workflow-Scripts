# coding: utf-8
import requests
import typer
from icecream import ic

from change_version import debug_output_control, github_output

app = typer.Typer()


@app.command()
def get_version(url: str, debug: bool = False):
    debug_output_control(debug)
    ic(url)
    response = ic(requests.get(url))
    response.raise_for_status()
    github_output("get_version", ic(response.text))
    response.close()


if __name__ == "__main__":
    app()
