import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key-not-used")   # modules build models at import

import copy

import pytest

from nimbus import systems as ns

_SNAPSHOT = copy.deepcopy(ns.LEAVE_BALANCE)


@pytest.fixture(autouse=True)
def fresh_systems():
    """Every test starts with the mock company systems in their initial state."""
    ns.LEAVE_BALANCE.clear()
    ns.LEAVE_BALANCE.update(copy.deepcopy(_SNAPSHOT))
    for store in (ns.BOOKINGS, ns.LEAVE_REQUESTS, ns.TICKETS, ns.EMAILS, ns.MEETINGS):
        store.clear()
    yield
