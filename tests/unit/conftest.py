# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pytest

from acct_manager import moc_openshift
from acct_manager import models


def fake_response(status_code):
    return mock.Mock(status=status_code, status_code=status_code)


@pytest.fixture
def a_project():
    return models.Project.quick(
        name="test-project",
        labels={"massopen.cloud/project": "test-project"},
        annotations={"openshift.io/requester": "test-user"},
    )


@pytest.fixture
def a_group():
    return models.Group.quick(
        name="test-project-admin",
        labels={"massopen.cloud/project": "test-project"},
    )


@pytest.fixture
def moc():
    _moc = moc_openshift.MocOpenShift(
        mock.Mock(), "fake-idp", "fake-quotas", mock.Mock()
    )
    _moc.resources = mock.Mock()
    return _moc
