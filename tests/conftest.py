# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for convtools.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    https://pytest.org/latest/plugins.html
"""

import pytest


# https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option

def pytest_addoption(parser):
    parser.addoption(
        "--bench", action="store_true", default=False, help="run benchmarks"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "bench: mark test as benchmark")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--bench"):
        # --bench given in cli: do not skip benchmarks
        return

    if config.getoption("-m") == "bench":
        # -m bench
        return

    skip_benches = pytest.mark.skip(reason="need --bench option to run")

    for item in items:
        if "bench" in item.keywords:
            item.add_marker(skip_benches)
