# coding: utf-8
from icecream import ic

from change_version import new_version_handle

if __name__ == "__main__":
    ic(new_version_handle("v1.2.3"))
    ic(new_version_handle("v1.2.3-test.0"))
    ic(new_version_handle("vv1.2.3-test.0"))
    ic(new_version_handle("test"))
