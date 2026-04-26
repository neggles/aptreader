import unittest
from unittest.mock import patch

import reflex as rx

from aptreader.models import Architecture, Component, Distribution
from aptreader.states.packages import PackagesState


class _Result:
    def __init__(self, *, one=None, all_rows=None):
        self._one = one
        self._all_rows = [] if all_rows is None else all_rows

    def one_or_none(self):
        return self._one

    def all(self):
        return self._all_rows


class _Session:
    def __init__(self, first_result):
        self._first_result = first_result
        self.calls = []

    def exec(self, statement):
        self.calls.append(statement)
        if len(self.calls) == 1:
            return _Result(one=self._first_result)
        return _Result(all_rows=[])


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyState:
    def __init__(self):
        self.current_distro = Distribution(id=7, repository_id=42, name="bookworm")
        self.component_filter = "all"
        self.architecture_filter = "all"
        self.search_value = ""
        self.max_results = 250
        self.packages = []


class PackagesStateFilterQueryTests(unittest.TestCase):
    def test_component_lookup_does_not_cross_join_package_table(self):
        state = _DummyState()
        state.component_filter = "main"

        session = _Session(Component(id=10, repository_id=42, name="main"))
        with patch.object(rx, "session", lambda: _SessionContext(session)):
            PackagesState.load_packages.fn(state)

        component_lookup_sql = str(session.calls[0])
        self.assertNotIn("FROM component, package", component_lookup_sql)

    def test_architecture_lookup_does_not_cross_join_package_table(self):
        state = _DummyState()
        state.architecture_filter = "amd64"

        session = _Session(Architecture(id=11, repository_id=42, name="amd64"))
        with patch.object(rx, "session", lambda: _SessionContext(session)):
            PackagesState.load_packages.fn(state)

        architecture_lookup_sql = str(session.calls[0])
        self.assertNotIn("FROM architecture, package", architecture_lookup_sql)


if __name__ == "__main__":
    unittest.main()
