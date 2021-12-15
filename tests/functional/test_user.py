def test_user(session, a_user):
    res = session.get(f"/users/{a_user}")
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["metadata"]["name"] == a_user


def test_user_not_found(session):
    res = session.get("/users/missing-user")
    assert res.status_code == 404


def test_user_invalid(session):
    res = session.post("/users", json={})
    assert res.status_code == 400
