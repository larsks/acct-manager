# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
from unittest import mock

import json
import pytest

import acct_manager.api
from acct_manager import models, exc


@pytest.fixture
def openshift():
    return mock.Mock()


@pytest.fixture
def client(openshift):
    acct_manager.api.AUTH_DISABLED = True
    with mock.patch("acct_manager.api.get_openshift_client") as fake_get_client:
        fake_get_client.return_value = openshift
        app = acct_manager.api.create_app(
            TESTING=True,
            IDENTITY_PROVIDER="fake",
            ADMIN_PASSWORD="fake",
            AUTH_DISABLED="true",
        )

        with app.test_client() as client:
            yield client


@pytest.fixture
def client_auth(openshift):
    acct_manager.api.AUTH_DISABLED = True
    with mock.patch("acct_manager.api.get_openshift_client") as fake_get_client:
        fake_get_client.return_value = openshift
        app = acct_manager.api.create_app(
            TESTING=True,
            IDENTITY_PROVIDER="fake",
            ADMIN_PASSWORD="fake",
        )

        with app.test_client() as client:
            yield client


def test_healthcheck(client_auth):
    """Test that we can reach the healthcheck endpoint when authentication
    is enabled and we are not providing any credentials."""
    res = client_auth.get("/healthz")
    assert res.status_code == 200
    assert b"OK" in res.data


def test_get_user_auth(client_auth):
    """Test that we receive a 401 Unauthorized response when we attempt
    to access an authenticated endpoint without providing credentials."""
    res = client_auth.get("/users/test-user")
    assert res.status_code == 401


def test_create_user(client):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.create_user_bundle"
    ) as fake_create_user_bundle:
        fake_create_user_bundle.return_value = models.User(
            metadata=models.Metadata(name="test-user"),
            fullName="Test User",
        )
        res = client.post(
            "/users",
            data=json.dumps({"name": "test-user"}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert not res.json["error"]
        user = models.User(**res.json["user"])
        assert user.metadata.name == "test-user"


def test_create_user_exists(client):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.create_user_bundle"
    ) as fake_create_user_bundle:
        fake_response = mock.Mock(status=409)
        fake_create_user_bundle.side_effect = exc.ConflictError(fake_response)
        res = client.post(
            "/users",
            data=json.dumps({"name": "test-user"}),
            content_type="application/json",
        )
        assert res.status_code == 409
        assert res.json["error"]
        assert res.json["message"] == "object already exists"


def test_get_user(client):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_user"
    ) as fake_get_user:
        fake_get_user.return_value = models.User(
            metadata=models.Metadata(name="test-user"),
        )
        res = client.get("/users/test-user")
        assert res.status_code == 200
        assert not res.json["error"]
        user = models.User(**res.json["user"])
        assert user.metadata.name == "test-user"


def test_get_user_missing(client):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_user"
    ) as fake_get_user:
        fake_response = mock.Mock(status=404)
        fake_get_user.side_effect = exc.NotFoundError(fake_response)
        res = client.get("/users/test-user")
        assert res.status_code == 404
        assert res.json["error"]


def test_delete_project_invalid(client):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.delete_project_bundle"
    ) as fake_delete_project_bundle:

        fake_delete_project_bundle.side_effect = exc.InvalidProjectError()
        res = client.delete("/projects/test-project")
        assert res.status_code == 403
