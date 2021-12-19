"""Pydantic models for the onboarding microservice API

Models marked with `_expose = True` are public facing models that will be
published in the OpenAPI schema.
"""

# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations

import enum
import re
from typing import Optional, Union, Any

from pydantic import BaseModel, validator, root_validator


# pylint: disable=unused-argument
def ensure_list(
    cls: BaseModel, value: Optional[list[Any]], values: dict[Any, Any]
) -> list[Any]:
    """Ensure an optional list returns an empty list instead of None"""
    if value is None:
        value = []
    return value


# pylint: disable=unused-argument
def remove_null_keys(
    cls: BaseModel, value: Optional[dict[str, str]], values: dict[Any, Any]
) -> Optional[dict[str, str]]:
    """Remove all keys with None values from dictionary"""
    if value is not None:
        to_delete = [k for k in value.keys() if value[k] is None]
        for k in to_delete:
            del value[k]

    return value


class UserRequest(BaseModel):
    """Request to create a user"""

    _expose: bool = True

    name: str
    fullName: Optional[str]

    # pylint: disable=no-self-use,no-self-argument,invalid-name
    @validator("fullName", always=True)
    def validate_fullName(cls, value: str, values: dict[str, Any]) -> str:
        """Default fullName to name if not provided"""
        if value is None:
            value = values.get("name")

        return value


class ProjectRequest(BaseModel):
    """Request to create a project"""

    _expose: bool = True

    name: str
    requester: str
    display_name: Optional[str]
    description: Optional[str]


class Metadata(BaseModel):
    """Standard Kubernetes metadata"""

    name: str
    labels: Optional[dict[str, Union[str, None]]]
    annotations: Optional[dict[str, Union[str, None]]]

    _remove_null_keys_labels = validator("labels", allow_reuse=True)(remove_null_keys)
    _remove_null_keys_annotations = validator("annotations", allow_reuse=True)(
        remove_null_keys
    )


class NamespacedMetadata(Metadata):
    """Standard Kubernetes metadata for a namespaced object"""

    namespace: str


class Resource(BaseModel):
    """Fields and methods common to all resources"""

    apiVersion: str
    kind: str
    metadata: Metadata

    @classmethod
    def quick(
        cls, name: str, namespace: Optional[str] = None, **kwargs: Any
    ) -> Resource:
        return cls(metadata=Metadata(name=name, namespace=namespace), **kwargs)


class NamespacedResource(Resource):
    """A Resource that requires a namespace"""

    metadata: NamespacedMetadata


class Project(Resource):
    """A project.openshift.io/v1 Project"""

    _expose: bool = True

    apiVersion: str = "project.openshift.io/v1"
    kind: str = "Project"

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @root_validator
    def validate_name(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        """Verify that project name matches kubernetes naming requirements"""
        fixed_name = (
            re.sub(r"[^\w]+", "-", values["metadata"].name, flags=re.ASCII)
            .lower()
            .strip("-")
        )
        if values["metadata"].name != fixed_name:
            raise ValueError(values["metadata"].name)
        return values


class Group(Resource):
    """A user.openshift.io/v1 Group"""

    _expose: bool = True

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Group"
    users: Optional[list[str]]

    _ensure_list_users = validator("users", allow_reuse=True, always=True)(ensure_list)


class User(Resource):
    """A user.openshift.io/v1 User"""

    _expose: bool = True

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


class Scope(str, enum.Enum):
    """Valid quota scope values"""

    Project = "Project"
    BestEffort = "BestEffort"
    NotBestEffort = "NotBestEffort"
    Terminating = "Terminating"
    NotTerminating = "NotTerminating"


class ResourceQuotaSpec(BaseModel):
    """Spec for a v1 ResourceQuota"""

    # pylint: disable=missing-class-docstring
    class Config:
        use_enum_values = True

    hard: Optional[dict[str, str]]
    scopes: Optional[list[Scope]]


class ResourceQuota(NamespacedResource):
    """A v1 ResourceQuota"""

    _expose: bool = True

    apiVersion: str = "v1"
    kind: str = "ResourceQuota"
    spec: ResourceQuotaSpec


class LimitDef(BaseModel):
    """Defines limits for a single type"""

    type: str
    max: Optional[dict[str, str]]
    min: Optional[dict[str, str]]
    default: Optional[dict[str, str]]
    defaultRequest: Optional[dict[str, str]]
    maxLimitRequestRatio: Optional[dict[str, str]]


class LimitRangeSpec(BaseModel):
    """Spec portion of a v1 LimitRange"""

    limits: Optional[list[LimitDef]]

    _ensure_list_limits = validator("limits", allow_reuse=True, always=True)(
        ensure_list
    )


class LimitRange(NamespacedResource):
    """A v1 LimitRange"""

    _expose: bool = True

    apiVersion: str = "v1"
    kind: str = "LimitRange"
    metadata: NamespacedMetadata
    spec: LimitRangeSpec


class QuotaRequest(BaseModel):
    """A quota request"""

    _expose: bool = True

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

    _expose: bool = True

    error: bool
    message: Optional[str]


class ProjectResponse(Response):
    """API response that contains a project"""

    _expose: bool = True

    project: Project


class UserResponse(Response):
    """API response that contains a user"""

    _expose: bool = True

    user: User


class QuotaResponse(Response):
    """API response that contains quota information"""

    _expose: bool = True

    quotas: list[ResourceQuota]
    limits: list[LimitRange]


class RoleResponseData(BaseModel):
    """API response that contains role membership information"""

    user: str
    project: str
    role: str
    has_role: bool


class RoleResponse(Response):
    """Response when querying if user has a given role in project"""

    _expose: bool = True

    role: RoleResponseData


class GroupResponse(Response):
    """API response that contains a group"""

    _expose: bool = True

    group: Group


class ScaledValue(BaseModel):
    """Represents a value that can be scaled by a multiplier"""

    base: int
    coefficient: float
    units: Optional[str]

    def resolve(self, multiplier: int = 1) -> str:
        """Convert base, coefficient, and multiplier into a value.

        If coefficient is 0, base is used unmodified. Otherwise the value
        is base * coefficient * multiplier."""
        if self.coefficient == 0:
            value = self.base
        else:
            value = round(self.base * self.coefficient * multiplier)

        units = self.units if self.units else ""
        return f"{value}{units}"


class QFLimitSpec(BaseModel):
    """Limit specification"""

    type: str
    max: Optional[dict[str, ScaledValue]]
    min: Optional[dict[str, ScaledValue]]
    default: Optional[dict[str, ScaledValue]]
    defaultRequest: Optional[dict[str, ScaledValue]]
    maxLimitRequestRatio: Optional[dict[str, ScaledValue]]


class QFQuotaSpec(BaseModel):
    """Quota specification"""

    scopes: list[Scope]
    values: dict[str, ScaledValue]


class QuotaFile(BaseModel):
    """Quota definition file"""

    _expose: bool = True

    quotas: Optional[list[QFQuotaSpec]]
    limits: Optional[list[QFLimitSpec]]

    _ensure_list_quotas = validator("quotas", allow_reuse=True, always=True)(
        ensure_list
    )
    _ensure_list_limits = validator("limits", allow_reuse=True, always=True)(
        ensure_list
    )
