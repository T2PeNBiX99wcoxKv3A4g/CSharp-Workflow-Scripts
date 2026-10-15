# coding: utf-8
from icecream import ic

from change_version import InvalidVersionError, normalize_version

if __name__ == "__main__":
    ic(normalize_version("v1.2.3"))
    ic(normalize_version("v1.2.3-test.0"))
    ic(normalize_version("vv1.2.3-test.0"))
    try:
        ic(normalize_version("test"))
    except InvalidVersionError as error:
        ic(error)
