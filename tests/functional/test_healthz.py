def test_healthz(session):
    res = session.get("/healthz")
    assert res.text == "OK"
