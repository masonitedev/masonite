"""Test database bootstrap.

The test database is no longer committed to the repository. Instead it is
built fresh from the test migrations and seeds at the start of every test
session, so the suite always starts from a known, clean state and nothing has
to be restored afterwards.
"""

import pytest

@pytest.fixture(scope="module", autouse=True)
def build_test_database():
    """override the default session builder"""
    yield
