# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
from acct_manager import models


def test_project(session, a_project):
    """Verify that we created a project with the expected name"""
    res = session.get(f"/projects/{a_project}")
    assert res.status_code == 200
    data = res.json()
    assert data["project"]["metadata"]["name"] == a_project


def test_project_not_found(session):
    """Verify that we get a 404 error for a project that does not exist"""
    res = session.get("/projects/missing-project")
    assert res.status_code == 404


def test_project_create_invalid(session):
    """Verify we receive an error when submitting a request missing required fields"""
    res = session.post("/projects", json={})
    assert res.status_code == 400


def test_project_delete_invalid(session, ocp_api, suffix):
    """Verify that we are unable to delete a project not created by the onboarding api"""
    name = f"target-project-{suffix}"
    project = models.Project(
        metadata=models.Metadata(name=name),
    )
    projects = ocp_api.resources.get(
        api_version="project.openshift.io/v1", kind="Project"
    )
    try:
        projects.create(body=project.dict(exclude_none=True))
        res = session.delete(f"/projects/{name}")
        assert res.status_code == 400
    finally:
        projects.delete(name=name)
