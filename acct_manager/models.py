"""Pydantic models for the onboarding microservice API

Models marked with @expose (and their dependencies) will be published in the
OpenAPI schema.
"""

# https://www.python.org/dev/peps/pep-0563/
from __future__ import annotations

import enum
import re
from typing import Optional, Union, Type, TypeVar, Any

from pydantic import BaseModel, validator, root_validator

public_models: list[Type[BaseModel]] = []


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


def expose(cls: Any) -> Any:
    """Mark model as exposed in public api"""
    public_models.append(cls)
    return cls


@expose
class UserRequest(BaseModel):
    """Request to create a user"""

    name: str
    fullName: Optional[str]

    # pylint: disable=no-self-use,no-self-argument,invalid-name
    @validator("fullName", always=True)
    def validate_fullName(cls, value: str, values: dict[str, Any]) -> str:
        """Default fullName to name if not provided"""
        if value is None:
            value = values.get("name")

        return value


@expose
class ProjectRequest(BaseModel):
    """Request to create a project"""

    name: str
    requester: str
    display_name: Optional[str]
    description: Optional[str]


class Metadata(BaseModel):
    """Standard Kubernetes metadata"""

    name: str
    labels: Optional[dict[str, Optional[str]]]
    annotations: Optional[dict[str, Optional[str]]]

    _remove_null_keys_labels = validator("labels", allow_reuse=True)(remove_null_keys)
    _remove_null_keys_annotations = validator("annotations", allow_reuse=True)(
        remove_null_keys
    )


class NamespacedMetadata(Metadata):
    """Standard Kubernetes metadata for a namespaced object"""

    namespace: str


TResource = TypeVar("TResource", bound="Resource")


class Resource(BaseModel):
    """Fields and methods common to all resources"""

    apiVersion: str
    kind: str
    metadata: Metadata

    @classmethod
    def quick(
        cls: Type[TResource],
        name: str,
        namespace: Optional[str] = None,
        labels: Optional[dict[str, Optional[str]]] = None,
        annotations: Optional[dict[str, Optional[str]]] = None,
        **kwargs: Any,
    ) -> TResource:
        """Convenience method for creating new resource"""
        metadata: Union[Metadata, NamespacedMetadata]
        mdclass: Union[Type[Metadata], Type[NamespacedMetadata]]

        if namespace:
            mdclass = NamespacedMetadata
        else:
            mdclass = Metadata

        metadata = mdclass(
            name=name, namespace=namespace, labels=labels, annotations=annotations
        )

        return cls(metadata=metadata, **kwargs)


class NamespacedResource(Resource):
    """A Resource that requires a namespace"""

    metadata: NamespacedMetadata


class Project(Resource):
    """A project.openshift.io/v1 Project"""

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

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Group"
    users: Optional[list[str]]

    _ensure_list_users = validator("users", allow_reuse=True, always=True)(ensure_list)


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

    # pylint: disable=unused-argument,no-self-argument,no-self-use
    @root_validator
    def validate_name(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        """Verify that project name matches kubernetes naming requirements"""
        if ":" not in values["metadata"].name:
            raise ValueError(
                "identity name must be in the format providerName:providerUserName"
            )
        return values


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

    # pylint: disable=missing-class-docstring,too-few-public-methods
    class Config:
        use_enum_values = True

    hard: Optional[dict[str, str]]
    scopes: Optional[list[Scope]]


class ResourceQuota(NamespacedResource):
    """A v1 ResourceQuota"""

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

    apiVersion: str = "v1"
    kind: str = "LimitRange"
    metadata: NamespacedMetadata
    spec: LimitRangeSpec


@expose
class QuotaRequest(BaseModel):
    """A quota request"""

    multiplier: int

    # pylint: disable=no-self-argument,unused-argument,no-self-use
    @validator("multiplier")
    def validate_multiplier(cls, value: int, values: dict[str, Any]) -> int:
        """Ensure that multiplier is positive"""
        if value <= 0:
            raise ValueError(value)
        return value


@expose
class Response(BaseModel):
    """An API response object"""

    error: bool
    message: Optional[str]


@expose
class ProjectResponse(Response):
    """API response that contains a project"""

    project: Project


@expose
class UserResponse(Response):
    """API response that contains a user"""

    user: User


@expose
class QuotaResponse(Response):
    """API response that contains quota information"""

    quotas: list[ResourceQuota]
    limits: list[LimitRange]


class RoleResponseData(BaseModel):
    """API response that contains role membership information"""

    user: str
    project: str
    role: str
    has_role: bool


@expose
class RoleResponse(Response):
    """Response when querying if user has a given role in project"""

    role: RoleResponseData


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


@expose
class QuotaFile(BaseModel):
    """Quota definition file"""

    quotas: Optional[list[QFQuotaSpec]]
    limits: Optional[list[QFLimitSpec]]

    _ensure_list_quotas = validator("quotas", allow_reuse=True, always=True)(
        ensure_list
    )
    _ensure_list_limits = validator("limits", allow_reuse=True, always=True)(
        ensure_list
    )
