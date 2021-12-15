def test_user_role(session, a_user, a_project):
    url = f"/users/{a_user}/projects/{a_project}/roles/admin"
    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert not data["object"]["has_role"]
    res = session.put(url)
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["users"] == [a_user]
    res = session.delete(url)
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["users"] == []
