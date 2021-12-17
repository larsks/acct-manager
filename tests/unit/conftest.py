# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pytest

from acct_manager import moc_openshift

fake_404_response = mock.Mock(status=404)


@pytest.fixture
def moc():
    _moc = moc_openshift.MocOpenShift(
        mock.Mock(), "fake_idp", "fake_quotas", mock.Mock()
    )
    _moc.resources = mock.Mock()
    return _moc
