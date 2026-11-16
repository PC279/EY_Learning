"""Test setup: no network, scripted models, fresh mock systems for every test."""
import copy
import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key-not-used")

import pytest  # noqa: E402

import nimbus.model  # noqa: E402
from nimbus import systems as ns  # noqa: E402
from tests import scripted  # noqa: E402

nimbus.model.init_chat_model = lambda *a, **k: scripted.ScriptedModel()   # every get_model() is scripted
_BALANCE = copy.deepcopy(ns.LEAVE_BALANCE)


@pytest.fixture(autouse=True)
def fresh():
    ns.LEAVE_BALANCE.clear()
    ns.LEAVE_BALANCE.update(copy.deepcopy(_BALANCE))
    for store in (ns.BOOKINGS, ns.LEAVE_REQUESTS, ns.TICKETS, ns.EMAILS, ns.MEETINGS):
        store.clear()
    scripted.SCRIPT.clear()
    scripted.SEEN.clear()
    yield
