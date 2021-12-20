# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pytest

from acct_manager import exc, models
from .conftest import fake_response


def test_qualify_user_name(moc):
    assert moc.qualify_user_name("test-user") == "fake-idp:test-user"


def test_get_user(moc):
    user = models.User.quick(name="test-user")
    moc.resources.users.get.return_value = user
    res = moc.get_user("test-user")
    assert res == user


def test_user_exists(moc):
    user = models.User.quick(name="test-user")
    moc.resources.users.get.return_value = user
    assert moc.user_exists("test-user")


def test_user_not_exists(moc):
    moc.resources.users.get.side_effect = exc.NotFoundError(fake_response(404))
    assert not moc.user_exists("test-user")


def test_create_user(moc):
    user = models.User.quick(
        name="test-user",
        fullName="Test User",
    )
    moc.resources.users.get.return_value = user
    moc.create_user("test-user", "Test User")
    assert (
        mock.call.create(body=user.dict(exclude_none=True))
        in moc.resources.users.method_calls
    )


def test_delete_user_exists(moc):
    user = models.User.quick(
        name="test-user",
        fullName="Test User",
    )
    moc.resources.users.get.return_value = user
    moc.delete_user("test-user")
    assert mock.call.delete(name="test-user") in moc.resources.users.method_calls


def test_delete_user_not_exists(moc):
    moc.resources.users.get.side_effect = exc.NotFoundError(fake_response(404))
    with pytest.raises(exc.NotFoundError):
        moc.delete_user("test-user")


def test_get_identity(moc):
    ident = models.Identity.quick(
        name="fake-idp:test-user",
        providerName="fake-idp",
        providerUserName="test-user",
    )
    moc.resources.identities.get.return_value = ident
    res = moc.get_identity("test-user")
    assert res.providerUserName == ident.providerUserName
    assert res.providerName == ident.providerName


def test_create_identity(moc):
    ident = models.Identity.quick(
        name="fake-idp:test-user",
        providerName="fake-idp",
        providerUserName="test-user",
    )
    moc.create_identity("test-user")
    moc.resources.identities.create.assert_called_with(
        body=ident.dict(exclude_none=True)
    )


def test_identity_exists(moc):
    ident = models.Identity.quick(
        name="fake-idp:test-user",
        providerName="fake-idp",
        providerUserName="test-user",
    )

    moc.resources.identities.get.return_value = ident
    assert moc.identity_exists("test-user")


def test_identity_exists_notfound(moc):
    moc.resources.identities.get.side_effect = exc.NotFoundError(fake_response(404))
    assert not moc.identity_exists("test-user")


def test_delete_identity(moc):
    ident = models.Identity.quick(
        name="fake-idp:test-user",
        providerName="fake-idp",
        providerUserName="test-user",
    )

    moc.resources.identities.get.return_value = ident

    moc.delete_identity("test-user")
    moc.resources.identities.delete.assert_called_with(name="fake-idp:test-user")
