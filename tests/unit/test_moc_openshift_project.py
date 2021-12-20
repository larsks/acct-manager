# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore
from unittest import mock

import pydantic
import pytest

from acct_manager import exc, models
from .conftest import fake_response


def test_get_project(moc, a_project):
    moc.resources.projects.get.return_value = a_project
    res = moc.get_project("test-project")
    assert res == a_project


def test_project_exists(moc, a_project):
    moc.resources.projects.get.return_value = a_project
    assert moc.project_exists("test-project")


def test_project_not_exists(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_response(404))
    assert not moc.project_exists("test-project")


def test_get_project_unsafe(moc):
    project = models.Project.quick(name="test-project")
    moc.resources.projects.get.return_value = project

    with pytest.raises(exc.InvalidProjectError):
        moc.get_project("test-project")


def test_create_project(moc, a_project):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_response(404))
    moc.create_project("test-project", "test-user")
    assert (
        mock.call.projects.create(body=a_project.dict(exclude_none=True))
        in moc.resources.method_calls
    )


def test_create_project_exists(moc, a_project):
    moc.resources.projects.get.return_value = a_project

    with pytest.raises(exc.ProjectExistsError):
        moc.create_project("test-project", "test-user")


def test_delete_project_exists(moc, a_project):
    moc.resources.projects.get.return_value = a_project

    moc.delete_project("test-project")
    assert mock.call.delete(name="test-project") in moc.resources.projects.method_calls


def test_delete_project_not_exists(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_response(404))
    with pytest.raises(exc.NotFoundError):
        moc.delete_project("test-project")
    assert (
        mock.call.delete(name="test-project") not in moc.resources.projects.method_calls
    )


def test_delete_project_invalid_target(moc):
    project = models.Project.quick(name="test-project")
    moc.resources.projects.get.return_value = project

    with pytest.raises(exc.InvalidProjectError):
        moc.delete_project("test-project")


def test_create_project_invalid_name(moc):
    moc.resources.projects.get.side_effect = exc.NotFoundError(fake_response(404))
    with pytest.raises(pydantic.error_wrappers.ValidationError):
        moc.create_project("Invalid Name", "test-user")
