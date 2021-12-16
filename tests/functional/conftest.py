"""Common fixtures for functional tests"""

# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
import os
import random
import string
import time
import urllib.parse
import warnings

import dotenv
import kubernetes
import openshift.dynamic
import pytest
import requests

from acct_manager import models

dotenv.load_dotenv()


class Session(requests.Session):
    def __init__(self):
        super().__init__()
        self.endpoint = os.environ["ACCT_MGR_API_ENDPOINT"]
        self.verify = False
        self.auth = ("admin", os.environ["ACCT_MGR_ADMIN_PASSWORD"])
        self.headers["content-type"] = "application/json"

    # pylint: disable=arguments-differ
    def request(self, method, url, **kwargs):
        if not url.startswith("http"):
            url = urllib.parse.urljoin(self.endpoint, url)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return super().request(method, url, **kwargs)


@pytest.fixture
def suffix():
    return "".join(random.sample(string.ascii_lowercase + string.digits, 6))


@pytest.fixture
def session():
    return Session()


@pytest.fixture
def a_user(session, suffix):
    name = f"test-user-{suffix}"
    req = models.UserRequest(name=name, fullName="Test User")
    res = session.post("/users", json=req.dict(exclude_none=True))
    assert res.status_code == 200
    yield name
    res = session.delete(f"/users/{name}")
    assert res.status_code == 200
    res = session.get(f"/users/{name}")
    assert res.status_code == 404


@pytest.fixture
def a_project(session, suffix):
    name = f"test-project-{suffix}"
    req = models.ProjectRequest(name=name, requester="test-user")
    res = session.post(
        "/projects",
        json=req.dict(exclude_none=True),
    )
    assert res.status_code == 200
    yield name
    res = session.delete(f"/projects/{name}")
    while True:
        res = session.get(f"/projects/{name}")
        if res.status_code == 404:
            break
        assert res.status_code == 200
        time.sleep(1)


@pytest.fixture
def k8s_api():
    k8s_api = kubernetes.config.new_client_from_config()
    return k8s_api


@pytest.fixture
def ocp_api(k8s_api):
    dyn_api = openshift.dynamic.DynamicClient(k8s_api)
    return dyn_api
