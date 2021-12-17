# type: ignore
"""Test quota API

This test will attempt to create up to 10 configmaps in a project in order
to violate the quota. For this test to succeed, your active quota definitions
must set a limit (of less than 10) on the number of ConfigMaps.
"""

from openshift.dynamic.exceptions import ForbiddenError
import pytest

# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
from acct_manager import models


class ConfigMap(models.NamespacedResource):
    apiVersion: str = "v1"
    kind: str = "ConfigMap"
    data: dict[str, str]


def create_configmaps(ocp_api, project, count, base=0):
    cmapi = ocp_api.resources.get(api_version="v1", kind="ConfigMap")

    for i in range(base, base + count):
        cm = ConfigMap(
            metadata=models.NamespacedMetadata(
                name=f"example-cm-{i}", namespace=project
            ),
            data={"foo": "bar"},
        )
        cmapi.create(body=cm.dict(exclude_none=True))


def delete_configmaps(ocp_api, project, count, base=0):
    cmapi = ocp_api.resources.get(api_version="v1", kind="ConfigMap")

    for i in range(base, base + count):
        cmapi.delete(name=f"example-cm-{i}", namespace=project)


def test_quota(session, a_project, ocp_api):
    url = f"/projects/{a_project}/quotas"

    # check that quotas are initially empty
    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert data["quotas"]["items"] == []

    # this should succeed because there is no quota in place
    create_configmaps(ocp_api, a_project, 10)
    delete_configmaps(ocp_api, a_project, 10)

    # add a quota to the project
    quotarequest = models.QuotaRequest(multiplier=1)
    res = session.put(url, json=quotarequest.dict())
    assert res.status_code == 200

    # check that the project now has a quota
    res = session.get(url)
    assert res.status_code == 200
    data = res.json()
    assert len(data["quotas"]["items"]) >= 1

    # attempt to violate quota
    with pytest.raises(ForbiddenError):
        create_configmaps(ocp_api, a_project, 10)

    # delete the quota
    res = session.delete(url)
    assert res.status_code == 200
    res = session.get(url)

    # check that quotas have been deleted
    assert res.status_code == 200
    data = res.json()
    assert data["quotas"]["items"] == []
