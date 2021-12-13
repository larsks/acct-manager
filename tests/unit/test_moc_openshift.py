import pytest

from unittest import mock

import acct_manager.moc_openshift
from acct_manager import exc


@pytest.fixture
def api():
    return mock.MagicMock()


@pytest.fixture
def logger():
    return mock.MagicMock()


@pytest.fixture
def moc(api, logger):
    _moc = acct_manager.moc_openshift.MocOpenShift(api, "fake", logger)
    return _moc


def test_create_project(moc, api):
    expected = {
        "apiVersion": "project.openshift.io/v1",
        "kind": "Project",
        "metadata": {
            "name": "test-project",
            "labels": {
                "massopen.cloud/project": "test-project",
            },
            "annotations": {
                "openshift.io/requester": "test-requester",
            },
        },
    }

    fake_response = mock.Mock(status=404)

    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_project"
    ) as fake_get_project:
        fake_get_project.side_effect = exc.NotFoundError(fake_response)
        moc.create_project("test-project", "test-requester")
        assert mock.call.resources.get().create(body=expected) in api.mock_calls


def test_create_project_exists(moc, api):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.project_exists"
    ) as fake_project_exists:
        fake_project_exists.return_value = True
        with pytest.raises(exc.ProjectExistsError):
            moc.create_project("test-project", "test-requester")


def test_delete_project(moc, api):
    with mock.patch("acct_manager.moc_openshift.MocOpenShift.get_project"):
        moc.delete_project("test-project")
        assert mock.call.resources.get().delete(name="test-project") in api.mock_calls


def test_delete_project_not_exists(moc, api):
    fake_response = mock.Mock(status=404)

    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_project"
    ) as fake_get_project:
        fake_get_project.side_effect = exc.NotFoundError(fake_response)
        with pytest.raises(exc.NotFoundError):
            moc.delete_project("test-project")
        assert (
            mock.call.resources.get().delete(name="test-project") not in api.mock_calls
        )


def test_delete_project_invalid(moc, api):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_project"
    ) as fake_get_project:
        fake_get_project.side_effect = exc.InvalidProjectError()
        with pytest.raises(exc.InvalidProjectError):
            moc.delete_project("test-project")


def test_create_group(moc, api):
    expected = {
        "apiVersion": "user.openshift.io/v1",
        "kind": "Group",
        "metadata": {
            "name": "test-group",
            "labels": {
                "massopen.cloud/project": "test-project",
            },
        },
    }

    fake_response = mock.Mock(status=404)

    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_group"
    ) as fake_get_group:
        fake_get_group.side_effect = exc.NotFoundError(fake_response)
        moc.create_group("test-group", "test-project")
        assert mock.call.resources.get().create(body=expected) in api.mock_calls


def test_delete_group(moc, api):
    with mock.patch("acct_manager.moc_openshift.MocOpenShift.get_group"):
        moc.delete_group("test-group")
        assert mock.call.resources.get().delete(name="test-group") in api.mock_calls


def test_delete_group_not_exists(moc, api):
    fake_response = mock.Mock(status=404)

    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_group"
    ) as fake_get_group:
        fake_get_group.side_effect = exc.NotFoundError(fake_response)
        moc.delete_group("test-group")
        assert mock.call.resources.get().delete(name="test-group") not in api.mock_calls


def test_delete_group_invalid(moc, api):
    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_group"
    ) as fake_get_group:
        fake_get_group.side_effect = exc.InvalidProjectError()
        with pytest.raises(exc.InvalidProjectError):
            moc.delete_group("test-group")


def test_create_project_bundle(moc, api):
    fake_response = mock.Mock(status=404)

    expected = [
        {
            "apiVersion": "project.openshift.io/v1",
            "kind": "Project",
            "metadata": {
                "name": "test-project",
                "labels": {"massopen.cloud/project": "test-project"},
                "annotations": {"openshift.io/requester": "test-requester"},
            },
        },
        {
            "apiVersion": "user.openshift.io/v1",
            "kind": "Group",
            "metadata": {
                "name": "test-project-admin",
                "labels": {"massopen.cloud/project": "test-project"},
            },
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": "test-project-admin", "namespace": "test-project"},
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "ClusterRole",
                "name": "admin",
            },
            "subjects": [
                {
                    "kind": "Group",
                    "namespace": "test-project",
                    "name": "test-project-admin",
                }
            ],
        },
        {
            "apiVersion": "user.openshift.io/v1",
            "kind": "Group",
            "metadata": {
                "name": "test-project-member",
                "labels": {"massopen.cloud/project": "test-project"},
            },
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": "test-project-member", "namespace": "test-project"},
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "ClusterRole",
                "name": "edit",
            },
            "subjects": [
                {
                    "kind": "Group",
                    "namespace": "test-project",
                    "name": "test-project-member",
                }
            ],
        },
        {
            "apiVersion": "user.openshift.io/v1",
            "kind": "Group",
            "metadata": {
                "name": "test-project-reader",
                "labels": {"massopen.cloud/project": "test-project"},
            },
        },
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": "test-project-reader", "namespace": "test-project"},
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "ClusterRole",
                "name": "view",
            },
            "subjects": [
                {
                    "kind": "Group",
                    "namespace": "test-project",
                    "name": "test-project-reader",
                }
            ],
        },
    ]

    with mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_group"
    ) as fake_get_group, mock.patch(
        "acct_manager.moc_openshift.MocOpenShift.get_project"
    ) as fake_get_project:
        fake_get_project.side_effect = exc.NotFoundError(fake_response)
        fake_get_group.side_effect = exc.NotFoundError(fake_response)
        moc.create_project_bundle("test-project", "test-requester")

        for rsrc in expected:
            assert mock.call.resources.get().create(body=rsrc) in api.mock_calls
