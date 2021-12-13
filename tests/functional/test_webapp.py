import os
import time
import urllib.parse
import warnings

import dotenv
import pytest
import requests

dotenv.load_dotenv()


class Session(requests.Session):
    def __init__(self):
        super().__init__()
        self.endpoint = os.environ["ACCT_MGR_API_ENDPOINT"]
        self.verify = False
        self.auth = ("admin", os.environ["ACCT_MGR_ADMIN_PASSWORD"])
        self.headers["content-type"] = "application/json"

    def request(self, method, url, **kwargs):
        if not url.startswith("http"):
            url = urllib.parse.urljoin(self.endpoint, url)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return super().request(method, url, **kwargs)


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def a_user(session):
    res = session.post("/users", json={"name": "test-user", "fullName": "Test User"})
    assert res.status_code == 200
    yield res
    res = session.delete("/users/test-user")
    assert res.status_code == 200
    res = session.get("/users/test-user")
    assert res.status_code == 404


@pytest.fixture
def a_project(session):
    res = session.post(
        "/projects", json={"name": "test-project", "requester": "test_user"}
    )
    assert res.status_code == 200
    yield res
    while True:
        res = session.delete("/projects/test-project")
        if res.status_code == 404:
            break

        assert res.status_code == 200
        time.sleep(1)


def test_health(session):
    res = session.get("/healthz")
    assert res.text == "OK"


def test_user(session, a_user):
    res = session.get("/users/test-user")
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["metadata"]["name"] == "test-user"


def test_project(session, a_project):
    res = session.get("/projects/test-project")
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["metadata"]["name"] == "test-project"


def test_user_role(session, a_user, a_project):
    res = session.get("/users/test_user/projects/test-project/roles/admin")
    assert res.status_code == 200
    data = res.json()
    assert not data["object"]["has_role"]
    res = session.put("/users/test_user/projects/test-project/roles/admin")
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["users"] == ["test_user"]
    res = session.delete("/users/test_user/projects/test-project/roles/admin")
    assert res.status_code == 200
    data = res.json()
    assert data["object"]["users"] == []
