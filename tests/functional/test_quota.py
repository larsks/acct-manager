from acct_manager import models


def test_quota(session, a_project):
    url = f"/projects/{a_project}/quotas"

    # check that quotas are initially empty
    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["items"] == []

    # add a quota to the project
    quotarequest = models.QuotaRequest(multiplier=1)
    res = session.put(url, json=quotarequest.dict())
    assert res.status_code == 200

    # check that the project now has a quota
    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert len(data["object"]["items"]) >= 1

    # delete the quota
    res = session.delete(url)
    assert res.status_code == 200
    res = session.get(url)

    # check that quotas have been deleted
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["items"] == []
