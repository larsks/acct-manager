# pylint: disable=unused-import
from kubernetes.client.exceptions import ApiException  # noqa

# pylint: disable=unused-import
from openshift.dynamic.exceptions import NotFoundError, ConflictError  # noqa


class AccountManagerError(Exception):
    def __init__(self, *args, obj=None):
        self.obj = obj
        super().__init__(*args)


class InvalidProjectError(AccountManagerError):
    pass


class ProjectExistsError(AccountManagerError):
    pass


class GroupExistsError(AccountManagerError):
    pass


class InvalidRoleNameError(AccountManagerError):
    pass
