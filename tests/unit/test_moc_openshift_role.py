# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore

"""Test role related behavior"""

import pytest
from unittest import mock

from acct_manager import models
from acct_manager import exc
from acct_manager import moc_openshift


def test_check_role_valid():
    moc_openshift.check_role_name("admin")


def test_check_role_invalid():
    with pytest.raises(exc.InvalidRoleNameError):
        moc_openshift.check_role_name("invalid")


def test_user_has_role(moc, a_project):
    group = models.Group.quick(
        name="test-project-admin",
        labels={"massopen.cloud/project": "test-project"},
        users=["test-user"],
    )

    moc.resources.projects.get.return_value = a_project
    moc.resources.groups.get.return_value = group
    res = moc.user_has_role("test-user", "test-project", "admin")
    assert res


def test_user_not_has_role(moc, a_project, a_group):
    moc.resources.projects.get.return_value = a_project
    moc.resources.groups.get.return_value = a_group
    res = moc.user_has_role("test-user", "test-project", "admin")
    assert not res


def test_add_user_to_role(moc, a_project, a_group):
    moc.resources.projects.get.return_value = a_project
    moc.resources.groups.get.return_value = a_group
    res = moc.get_group("test-group")
    assert res.users == []
    res = moc.add_user_to_role("test-user", "test-project", "admin")
    assert res.users == ["test-user"]


def test_remove_user_from_role(moc, a_project, a_group):
    moc.resources.projects.get.return_value = a_project
    moc.resources.groups.get.return_value = a_group
    a_group.users = ["test-user"]
    res = moc.get_group("test-group")
    assert res.users == ["test-user"]
    res = moc.remove_user_from_role("test-user", "test-project", "admin")
    assert res.users == []
    moc.resources.groups.patch.assert_called()


def test_remove_user_from_role_not_exist(moc, a_project, a_group):
    moc.resources.projects.get.return_value = a_project
    moc.resources.groups.get.return_value = a_group
    res = moc.get_group("test-group")
    assert res.users == []
    res = moc.remove_user_from_role("test-user", "test-project", "admin")
    assert res.users == []
    moc.resources.groups.patch.assert_not_called()


def test_remove_user_from_all_groups(moc):
    groups = [
        models.Group.quick(name="test-group-1", users=["test-user"]),
        models.Group.quick(name="test-group-2", users=["test-user"]),
    ]

    moc.resources.groups.get.return_value = mock.Mock(items=groups)
    moc.remove_user_from_all_groups("test-user")

    groups[0].users = []
    groups[1].users = []

    for group in groups:
        assert (
            mock.call.patch(body=group.dict(exclude_none=True))
            in moc.resources.groups.method_calls
        )
