"""Pydantic models for the onboarding microservice API"""

# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations


import re
from typing import Optional, Union, Any

from pydantic import BaseModel, validator

VALID_SCOPE_NAMES = (
    "Terminating",
    "NotTerminating",
    "BestEffort",
    "NotBestEffort",
)


class UserRequest(BaseModel):
    """Request to create a user"""

    name: str
    fullName: Optional[str]

    # pylint: disable=no-self-use,no-self-argument,invalid-name
    @validator("fullName", always=True)
    def validate_fullName(cls, value: str, values: dict[str, Any]) -> str:
        """Default fullName to name if not provided"""
        if value is None:
            return values.get("name")

        return value


class ProjectRequest(BaseModel):
    """Request to create a project"""

    name: str
    requester: str
    display_name: Optional[str]
    description: Optional[str]


def remove_null_keys(value: dict[str, str]) -> dict[str, str]:
    """Remove all keys with None values from dictionary"""
    to_delete = [k for k in value.keys() if value[k] is None]
    for k in to_delete:
        del value[k]

    return value


class Metadata(BaseModel):
    """Standard Kubernetes metadata"""

    name: str
    labels: Optional[dict[str, Union[str, None]]]
    annotations: Optional[dict[str, Union[str, None]]]

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @validator("labels")
    def validate_labels(
        cls, value: dict[str, str], values: dict[str, Any]
    ) -> dict[str, str]:
        """Ensure that there are no null labels"""
        if value is not None:
            value = remove_null_keys(value)
        return value

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @validator("annotations")
    def validate_annotations(
        cls, value: dict[str, str], values: dict[str, Any]
    ) -> dict[str, str]:
        """Ensure that there are no null annotations"""
        if value is not None:
            value = remove_null_keys(value)
        return value

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @validator("name")
    def validate_name(cls, name: str) -> str:
        """Verify that name matches kubernetes naming requirements"""
        fixed_name = re.sub(r"[^\w:]+", "-", name, flags=re.ASCII).lower().strip("-")
        if name != fixed_name:
            raise ValueError(name)
        return name


class NamespacedMetadata(Metadata):
    """Standard Kubernetes metadata for a namespaced object"""

    namespace: str


class Resource(BaseModel):
    """Fields and methods common to all resources"""

    apiVersion: str
    kind: str
    metadata: Metadata


class NamespacedResource(Resource):
    """A resource that requires a namespace"""

    metadata: NamespacedMetadata


class Project(Resource):
    """A project.openshift.io/v1 Project"""

    apiVersion: str = "project.openshift.io/v1"
    kind: str = "Project"


class Group(Resource):
    """A user.openshift.io/v1 Group"""

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Group"
    users: Optional[list[str]]

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @validator("users")
    def validate_users(cls, value: list[str], values: dict[str, Any]) -> list[str]:
        """Ensure that users is always a list.

        This simplifies code that wants to iterate over the list of
        users in a group.
        """
        return value if value else []


class User(Resource):
    """A user.openshift.io/v1 User"""

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "User"
    fullName: Optional[str]
    groups: Optional[list[str]]
    identities: Optional[list[str]]


class IdentityUser(BaseModel):
    """A convenience class for identities and useridentitymappings"""

    name: Optional[str]
    uid: Optional[str]


class Identity(Resource):
    """A user.openshift.io/v1 Identity

    This resource corresponds to information retrieved from an
    authentication source.
    """

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Identity"
    extra: Optional[dict[str, str]]
    providerName: str
    providerUserName: str
    user: Optional[IdentityUser]


class UserIdentityMapping(Resource):
    """A user.openshift.io/v1 UserIdentityMapping.

    This links a User object to an Identity object.
    """

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "UserIdentityMapping"
    user: IdentityUser
    identity: IdentityUser


class RoleRef(BaseModel):
    """Role reference part of a [cluster-]rolebinding"""

    apiGroup: str
    kind: str
    name: str


class Subject(BaseModel):
    """Subject reference part of a [cluster-]rolebinding"""

    kind: str
    namespace: Optional[str]
    name: str


class RoleBinding(NamespacedResource):
    """An rbac.authorization.k8s.io/v1 RoleBinding"""

    apiVersion: str = "rbac.authorization.k8s.io/v1"
    kind: str = "RoleBinding"
    roleRef: RoleRef
    subjects: list[Subject]


class QuotaSpec(BaseModel):
    """A single quota specification"""

    base: int
    coefficient: float
    units: Optional[str]

    # pylint: disable=no-self-argument,unused-argument,no-self-use
    @validator("coefficient")
    def validate_coefficient(cls, value: float, values: dict[str, Any]) -> float:
        """Ensure that coefficient is non-zero"""
        if value == 0:
            raise ValueError(value)
        return value


class QuotaFile(BaseModel):
    """Quota definition file"""

    Project: Optional[dict[str, QuotaSpec]]
    Terminating: Optional[dict[str, QuotaSpec]]
    NotTerminating: Optional[dict[str, QuotaSpec]]
    BestEffort: Optional[dict[str, QuotaSpec]]
    NotBestEffort: Optional[dict[str, QuotaSpec]]


class ResourceQuotaSpec(BaseModel):
    """Spec for a v1 ResourceQuota"""

    hard: Optional[dict[str, str]]
    scopes: Optional[list[str]]

    # pylint: disable=no-self-argument,unused-argument,no-self-use
    @validator("scopes")
    def validate_scopes(cls, value: list[str], values: dict[str, Any]) -> list[str]:
        """Ensure that scope name is valid"""
        for scope in value:
            if scope not in VALID_SCOPE_NAMES:
                raise ValueError(value)

        return value


class ResourceQuota(NamespacedResource):
    """A v1 ResourceQuota"""

    apiVersion: str = "v1"
    kind: str = "ResourceQuota"
    spec: ResourceQuotaSpec

    @classmethod
    def from_quotaspec(
        cls,
        name: str,
        project: str,
        scope: Optional[str],
        quotaspec: dict[str, str],
    ) -> ResourceQuota:
        """Transform quota values into a ResourceQuota"""
        spec = ResourceQuotaSpec(
            hard=quotaspec,
            scopes=[scope] if scope else [],
        )
        return cls(
            metadata=NamespacedMetadata(
                name=name, namespace=project, labels={"massopen.cloud/project": project}
            ),
            spec=spec,
        )


class ResourceQuotaList(BaseModel):
    """A list of v1 ResourceQuotas"""

    items: list[ResourceQuota]

    # pylint: disable=no-self-argument,unused-argument,no-self-use
    @validator("items", always=True)
    def validate_items(
        cls, value: list[ResourceQuota], values: dict[str, Any]
    ) -> list[ResourceQuota]:
        """Ensure items is always a list (and never None)"""
        if value is None:
            value = []

        return value

    @classmethod
    def from_api(cls, quotalist: Any) -> ResourceQuotaList:
        """Create a ResourceQuotaList from a list of quotas"""
        return cls(items=[ResourceQuota(**dict(item)) for item in quotalist.items])


class QuotaRequest(BaseModel):
    """A quota request"""

    multiplier: int

    # pylint: disable=no-self-argument,unused-argument,no-self-use
    @validator("multiplier")
    def validate_multiplier(cls, value: int, values: dict[str, Any]) -> int:
        """Ensure that multiplier is non-zero"""
        if value == 0:
            raise ValueError(value)
        return value


class Response(BaseModel):
    """An API response object"""

    error: bool
    message: Optional[str]


class ProjectResponse(Response):
    """API response that contains a project"""

    project: Project


class UserResponse(Response):
    """API response that contains a user"""

    user: User


class QuotaResponse(Response):
    """API response that contains quota information"""

    quotas: ResourceQuotaList


class RoleResponseData(BaseModel):
    """API response that contains role membership information"""

    user: str
    project: str
    role: str
    has_role: bool


class RoleResponse(Response):
    """Response when querying if user has a given role in project"""

    role: RoleResponseData


class GroupResponse(Response):
    """API response that contains a group"""

    group: Group
