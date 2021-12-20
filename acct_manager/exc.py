"""Exceptions raised by the acct_manager api"""

from typing import Union, Any

# pylint: disable=unused-import
from pydantic.error_wrappers import ValidationError  # noqa

# pylint: disable=unused-import
from kubernetes.client.exceptions import ApiException  # noqa

# pylint: disable=unused-import
from openshift.dynamic.exceptions import (  # noqa: F401
    NotFoundError,
    ConflictError,
    ForbiddenError,
)

from . import models


class AccountManagerError(Exception):
    """Base class for all exceptions defined by this package"""

    def __init__(self, *args: Any, obj: Union[None, models.Resource] = None) -> None:
        self.obj = obj
        super().__init__(*args)


class InvalidProjectError(AccountManagerError):
    """Raised on attempts to modify an invalid resource.

    This generally means attempts to delete a project or group that we
    didn't create.
    """


class NoQuotasError(AccountManagerError):
    """Raised on attempt to create quotas with no quota configuration"""


class ObjectExistsError(AccountManagerError):
    """Parent class for conflict errors"""


class ProjectExistsError(ObjectExistsError):
    """Raised when attempting to create a new project with a conflicting name"""


class GroupExistsError(ObjectExistsError):
    """Raised when attempting to create a new group with a conflicting name"""


class InvalidRoleNameError(AccountManagerError):
    """Raised when an invalid role name is used in a request"""
