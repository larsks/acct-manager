# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
from unittest import mock

import pytest

from acct_manager import exc, models
from .conftest import api_wrapper, fake_404_response


def test_get_user(moc):
    user = models.User(
        metadata=models.Metadata(
            name="test-user",
        )
    )
    moc.resources.users.get.return_value = api_wrapper(user)
    res = moc.get_user("test-user")
    assert res == user


def test_user_exists(moc):
    user = models.User(
        metadata=models.Metadata(
            name="test-user",
        )
    )
    moc.resources.users.get.return_value = api_wrapper(user)
    assert moc.user_exists("test-user")


def test_user_not_exists(moc):
    moc.resources.users.get.side_effect = exc.NotFoundError(fake_404_response)
    assert not moc.user_exists("test-user")


def test_create_user(moc):
    user = models.User(
        metadata=models.Metadata(
            name="test-user",
        ),
        fullName="Test User",
    )
    moc.resources.users.get.return_value = api_wrapper(user)
    moc.create_user("test-user", "Test User")
    assert (
        mock.call.create(body=user.dict(exclude_none=True))
        in moc.resources.users.method_calls
    )


def test_delete_user_exists(moc):
    user = models.User(
        metadata=models.Metadata(
            name="test-user",
        ),
        fullName="Test User",
    )
    moc.resources.users.get.return_value = api_wrapper(user)
    moc.delete_user("test-user")
    assert mock.call.delete(name="test-user") in moc.resources.users.method_calls


def test_delete_user_not_exists(moc):
    moc.resources.users.get.side_effect = exc.NotFoundError(fake_404_response)
    with pytest.raises(exc.NotFoundError):
        moc.delete_user("test-user")
