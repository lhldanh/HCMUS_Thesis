import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from ari.kg import get_kg


@pytest.fixture(scope="session")
def kg():
    return get_kg()
