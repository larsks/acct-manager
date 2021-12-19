# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
import json
from unittest import mock


def test_read_quota_file_missing(moc):
    with mock.patch(
        "acct_manager.moc_openshift.open", mock.mock_open(read_data="{}")
    ) as mock_open:
        mock_open.side_effect = FileNotFoundError()
        moc.read_quota_file()
        assert moc.quotas.quotas == []
        assert moc.quotas.limits == []


def test_read_quota_file_empty_map(moc):
    with mock.patch("acct_manager.moc_openshift.open", mock.mock_open(read_data="{}")):
        moc.read_quota_file()
        assert moc.quotas.quotas == []
        assert moc.quotas.limits == []


def test_read_quota_file_with_data(moc):
    data = {
        "limits": [
            {
                "type": "Container",
                "default": {"cpu": {"base": "500", "coefficient": "1", "units": "m"}},
            },
        ],
        "quotas": [
            {
                "scopes": ["Project"],
                "values": {
                    "memory": {"base": 1, "coefficient": "1", "units": "Gi"},
                },
            }
        ],
    }
    with mock.patch(
        "acct_manager.moc_openshift.open", mock.mock_open(read_data=json.dumps(data))
    ):
        moc.read_quota_file()
        assert moc.quotas.quotas[0].scopes == ["Project"]
        assert moc.quotas.limits[0].type == "Container"
