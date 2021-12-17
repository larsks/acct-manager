# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pydantic
import pytest

from acct_manager import exc, models
from .conftest import fake_404_response


def test_get_project(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.projects.get.return_value = project
    res = moc.get_project("test-project")
    assert res == project


def test_project_exists(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.projects.get.return_value = project
    assert moc.project_exists("test-project")


def test_project_not_exists(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    assert not moc.project_exists("test-project")


def test_get_project_unsafe(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project",
        )
    )
    moc.resources.projects.get.return_value = project

    with pytest.raises(exc.InvalidProjectError):
        moc.get_project("test-project")


def test_create_project(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project",
            labels={"massopen.cloud/project": "test-project"},
            annotations={"openshift.io/requester": "test-requester"},
        )
    )
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    moc.create_project("test-project", "test-requester")
    assert (
        mock.call.projects.create(body=project.dict(exclude_none=True))
        in moc.resources.method_calls
    )


def test_create_project_exists(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.projects.get.return_value = project

    with pytest.raises(exc.ProjectExistsError):
        moc.create_project("test-project", "test-requester")


def test_delete_project_exists(moc):
    project = models.Project(
        metadata=models.Metadata(
            name="test-project", labels={"massopen.cloud/project": "test-project"}
        )
    )
    moc.resources.projects.get.return_value = project

    moc.delete_project("test-project")
    assert mock.call.delete(name="test-project") in moc.resources.projects.method_calls


def test_delete_project_not_exists(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    with pytest.raises(exc.NotFoundError):
        moc.delete_project("test-project")
    assert (
        mock.call.delete(name="test-project") not in moc.resources.projects.method_calls
    )


def test_delete_project_invalid_target(moc):
    project = models.Project(metadata=models.Metadata(name="test-project"))
    moc.resources.projects.get.return_value = project

    with pytest.raises(exc.InvalidProjectError):
        moc.delete_project("test-project")


def test_create_project_invalid_name(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_404_response)
    with pytest.raises(pydantic.error_wrappers.ValidationError):
        moc.create_project("Invalid Name", "test-requester")
