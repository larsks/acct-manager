"""Test role granting/revoking"""


# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
def test_user_role(session, a_user, a_project):
    url = f"/users/{a_user}/projects/{a_project}/roles/admin"

    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert not data["role"]["has_role"]

    res = session.put(url)
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["has_role"]

    res = session.delete(url)
    assert res.status_code == 200
    data = res.json()
    assert not data["role"]["has_role"]
