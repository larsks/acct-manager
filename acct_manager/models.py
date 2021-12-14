from typing import Optional, Union

import pydantic

VALID_SCOPE_NAMES = (
    "Terminating",
    "NotTerminating",
    "BestEffort",
    "NotBestEffort",
)


class UserRequest(pydantic.BaseModel):
    """Request to create a user"""

    name: str
    fullName: Optional[str]

    @pydantic.validator("fullName", always=True)
    def validate_fullName(cls, value, values):  # pylint: disable=no-self-argument
        """Default fullName to name if not provided"""
        if value is None:
            return values.get("name")

        return value


class ProjectRequest(pydantic.BaseModel):
    """Request to create a project"""

    name: str
    requester: str
    display_name: Optional[str]
    description: Optional[str]


def remove_null_keys(value):
    """Remove all keys with None values from dictionary"""
    to_delete = [k for k in value.keys() if value[k] is None]
    for k in to_delete:
        del value[k]

    return value


class Metadata(pydantic.BaseModel):
    """Standard Kubernetes metadata"""

    name: str
    labels: Optional[dict[str, Union[str, None]]]
    annotations: Optional[dict[str, Union[str, None]]]

    @pydantic.validator("labels")
    def validate_labels(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        """Ensure that there are no null labels"""
        if value is not None:
            value = remove_null_keys(value)
        return value

    @pydantic.validator("annotations")
    def validate_annotations(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        """Ensure that there are no null annotations"""
        if value is not None:
            value = remove_null_keys(value)
        return value


class NamespacedMetadata(Metadata):
    """Standard Kubernetes metadata for a namespaced object"""

    namespace: str


class Resource(pydantic.BaseModel):
    """Fields and methods common to all resources"""

    apiVersion: str
    kind: str

    @classmethod
    def from_api(cls, res):
        """Transform an API response to a model"""
        return cls(**res.to_dict())


class Project(Resource):
    """A project.openshift.io/v1 Project"""

    apiVersion: str = "project.openshift.io/v1"
    kind: str = "Project"
    metadata: Metadata


class Group(Resource):
    """A user.openshift.io/v1 Group"""

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Group"
    metadata: Metadata
    users: Optional[list[str]]

    @pydantic.validator("users")
    def validate_users(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        """Ensure that users is always a list.

        This simplifies code that wants to iterate over the list of
        users in a group.
        """
        return value if value else []


class User(Resource):
    """A user.openshift.io/v1 User"""

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "User"
    metadata: Metadata
    fullName: Optional[str]
    groups: Optional[list[str]]
    identities: Optional[list[str]]


class identityUser(pydantic.BaseModel):
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
    metadata: Metadata
    extra: Optional[dict[str, str]]
    providerName: str
    providerUserName: str
    user: Optional[identityUser]


class UserIdentityMapping(Resource):
    """A user.openshift.io/v1 UserIdentityMapping.

    This links a User object to an Identity object.
    """

    apiVersion: str = "user.openshift.io/v1"
    kind: str = "UserIdentityMapping"
    user: identityUser
    identity: identityUser


class RoleRef(pydantic.BaseModel):
    """Role reference part of a [cluster-]rolebinding"""

    apiGroup: str
    kind: str
    name: str


class Subject(pydantic.BaseModel):
    """Subject reference part of a [cluster-]rolebinding"""

    kind: str
    namespace: Optional[str]
    name: str


class RoleBinding(Resource):
    """An rbac.authorization.k8s.io/v1 RoleBinding"""

    apiVersion: str = "rbac.authorization.k8s.io/v1"
    kind: str = "RoleBinding"
    metadata: NamespacedMetadata
    roleRef: RoleRef
    subjects: list[Subject]


class Response(pydantic.BaseModel):
    """An API response object"""

    error: bool
    message: Optional[str]
    object: Optional[pydantic.BaseModel]


class HasRoleResult(pydantic.BaseModel):
    """Response when querying if user has a given role in project"""

    user: str
    project: str
    role: str
    has_role: bool


class QuotaSpec(pydantic.BaseModel):
    """A single quota specification"""

    base: int
    coefficient: int
    units: Optional[str]

    @pydantic.validator("coefficient")
    def validate_coefficient(
        cls, value, values
    ):  # pylint: disable=no-self-argument,unused-argument
        """Ensure that coefficient is non-zero"""
        if value == 0:
            raise ValueError(value)
        return value


class QuotaFile(pydantic.BaseModel):
    """Quota definition file"""

    Project: Optional[dict[str, QuotaSpec]]
    Terminating: Optional[dict[str, QuotaSpec]]
    NotTerminating: Optional[dict[str, QuotaSpec]]
    BestEffort: Optional[dict[str, QuotaSpec]]
    NotBestEffort: Optional[dict[str, QuotaSpec]]


class ResourceQuotaSpec(pydantic.BaseModel):
    """Spec for a v1 ResourceQuota"""

    hard: Optional[dict[str, str]]
    scopes: Optional[list[str]]

    @pydantic.validator("scopes")
    def validate_scopes(
        cls, value, values
    ):  # pylint: disable=no-self-argument,unused-argument
        """Ensure that scope name is valid"""
        for scope in value:
            if scope not in VALID_SCOPE_NAMES:
                raise ValueError(value)

            return value


class ResourceQuota(Resource):
    """A v1 ResourceQuota"""

    apiVersion: str = "v1"
    kind: str = "ResourceQuota"
    metadata: NamespacedMetadata
    spec: ResourceQuotaSpec

    @classmethod
    def from_quotaspec(cls, name, project, scope, quotaspec):
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


class ResourceQuotaList(pydantic.BaseModel):
    """A list of v1 ResourceQuotas"""

    items: Optional[list[ResourceQuota]]

    @pydantic.validator("items", always=True)
    def validate_items(
        cls, value, values
    ):  # pylint: disable=no-self-argument,unused-argument
        """Ensure items is always a list (and never None)"""
        if value is None:
            value = []

        return value

    @classmethod
    def from_api(cls, quotalist):
        """Create a ResourceQuotaList from a list of quotas"""
        return cls(items=[ResourceQuota(**dict(item)) for item in quotalist.items])


class QuotaRequest(pydantic.BaseModel):
    """A quota request"""

    multiplier: int

    @pydantic.validator("multiplier")
    def validate_multiplier(
        cls, value, values
    ):  # pylint: disable=no-self-argument,unused-argument
        """Ensure that multiplier is non-zero"""
        if value == 0:
            raise ValueError(value)
        return value
