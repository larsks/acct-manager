"""Test healthcheck endpoint"""


# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
def test_healthz(session):
    res = session.get("/healthz")
    assert res.text == "OK"
