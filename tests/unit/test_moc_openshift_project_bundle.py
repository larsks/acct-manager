# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
from unittest import mock

import pytest

from acct_manager import exc, models
from .conftest import api_wrapper, fake_404_response

project_bundle = [
    models.Project(
        metadata=models.Metadata(
            name="test-project",
            labels={"massopen.cloud/project": "test-project"},
            annotations={"openshift.io/requester": "test-requester"},
        )
    ),
    models.Group(
        metadata=models.Metadata(
            name="test-project-admin",
            labels={"massopen.cloud/project": "test-project"},
        )
    ),
    models.Group(
        metadata=models.Metadata(
            name="test-project-member",
            labels={"massopen.cloud/project": "test-project"},
        )
    ),
    models.Group(
        metadata=models.Metadata(
            name="test-project-reader",
            labels={"massopen.cloud/project": "test-project"},
        )
    ),
    models.RoleBinding(
        metadata=models.NamespacedMetadata(
            namespace="test-project",
            name="test-project-admin",
        ),
        roleRef=models.RoleRef(
            apiGroup="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name="admin",
        ),
        subjects=[
            models.Subject(
                kind="Group",
                namespace="test-project",
                name="test-project-admin",
            ),
        ],
    ),
    models.RoleBinding(
        metadata=models.NamespacedMetadata(
            namespace="test-project",
            name="test-project-member",
        ),
        roleRef=models.RoleRef(
            apiGroup="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name="edit",
        ),
        subjects=[
            models.Subject(
                kind="Group",
                namespace="test-project",
                name="test-project-member",
            ),
        ],
    ),
    models.RoleBinding(
        metadata=models.NamespacedMetadata(
            namespace="test-project",
            name="test-project-reader",
        ),
        roleRef=models.RoleRef(
            apiGroup="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name="view",
        ),
        subjects=[
            models.Subject(
                kind="Group",
                namespace="test-project",
                name="test-project-reader",
            ),
        ],
    ),
]


def test_create_project_bundle(moc):
    expected = [x.dict(exclude_none=True) for x in project_bundle]

    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    moc.resources.groups.get.side_effect = exc.NotFoundError(fake_404_response)
    moc.create_project_bundle("test-project", "test-requester")

    create_calls = [
        call[2] for call in moc.resources.method_calls if "create" in call[0]
    ]

    for resource in expected:
        assert {"body": resource} in create_calls


def test_delete_project_bundle(moc):
    moc.resources.groups.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "Group"
    ]
    moc.resources.rolebindings.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "RoleBinding"
    ]
    moc.resources.projects.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "Project"
    ]
    moc.delete_project_bundle("test-project")

    for resource in project_bundle:
        assert resource.kind in ["Group", "RoleBinding", "Project"]
        if resource.kind == "Group":
            assert (
                mock.call.delete(name=resource.metadata.name)
                in moc.resources.groups.method_calls
            )
        elif resource.kind == "Project":
            assert (
                mock.call.delete(name=resource.metadata.name)
                in moc.resources.projects.method_calls
            )


def test_delete_project_bundle_group_notfound(moc):
    moc.resources.groups.get.side_effect = exc.NotFoundError(fake_404_response)
    moc.resources.rolebindings.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "RoleBinding"
    ]
    moc.resources.projects.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "Project"
    ]
    moc.delete_project_bundle("test-project")

    for resource in project_bundle:
        assert resource.kind in ["Group", "RoleBinding", "Project"]
        if resource.kind == "Group":
            assert (
                mock.call.delete(name=resource.metadata.name)
                not in moc.resources.groups.method_calls
            )
        elif resource.kind == "Project":
            assert (
                mock.call.delete(name=resource.metadata.name)
                in moc.resources.projects.method_calls
            )


def test_delete_project_bundle_project_notfound(moc):
    moc.resources.groups.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "Group"
    ]
    moc.resources.rolebindings.get.side_effect = [
        api_wrapper(x) for x in project_bundle if x.kind == "RoleBinding"
    ]
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    with pytest.raises(exc.NotFoundError):
        moc.delete_project_bundle("test-project")
