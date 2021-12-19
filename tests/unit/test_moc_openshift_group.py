# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pytest

from acct_manager import exc, models
from .conftest import fake_response


def test_create_group(moc):
    group = models.Group(
        metadata=models.Metadata(
            name="test-group", labels={"massopen.cloud/project": "test-project"}
        )
    )

    moc.resources.groups.get.side_effect = exc.NotFoundError(fake_response(404))
    moc.create_group("test-group", "test-project")
    assert (
        mock.call.create(body=group.dict(exclude_none=True))
        in moc.resources.groups.method_calls
    )


def test_create_group_exists(moc):
    group = models.Group(
        metadata=models.Metadata(
            name="test-group", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.groups.get.return_value = group

    with pytest.raises(exc.GroupExistsError):
        moc.create_group("test-group", "test-project")


def test_delete_group_exists(moc):
    group = models.Group(
        metadata=models.Metadata(
            name="test-group", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.groups.get.return_value = group

    moc.delete_group("test-group")
    assert mock.call.delete(name="test-group") in moc.resources.groups.method_calls


def test_delete_group_not_exists(moc):
    moc.resources.groups.get.side_effect = exc.NotFoundError(fake_response(404))

    moc.delete_group("test-group")
    assert mock.call.delete(name="test-group") not in moc.resources.groups.method_calls


def test_delete_group_invalid(moc):
    group = models.Group(metadata=models.Metadata(name="test-group"))
    moc.resources.groups.get.return_value = group

    with pytest.raises(exc.InvalidProjectError):
        moc.delete_group("test-group")
