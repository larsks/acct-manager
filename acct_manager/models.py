from typing import Optional, Union

import pydantic


class UserRequest(pydantic.BaseModel):
    name: str
    fullName: Optional[str]

    @pydantic.validator("fullName", always=True)
    def validate_fullName(cls, value, values):  # pylint: disable=no-self-argument
        if value is None:
            return values["name"]

        return value


class ProjectRequest(pydantic.BaseModel):
    name: str
    requester: str
    display_name: Optional[str]
    description: Optional[str]


def remove_null_keys(value):
    to_delete = [k for k in value.keys() if value[k] is None]
    for k in to_delete:
        del value[k]

    return value


class OwnerReference(pydantic.BaseModel):
    pass


class Metadata(pydantic.BaseModel):
    name: str
    labels: Optional[dict[str, Union[str, None]]]
    annotations: Optional[dict[str, Union[str, None]]]

    @pydantic.validator("labels")
    def validate_labels(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        if value is not None:
            value = remove_null_keys(value)
        return value

    @pydantic.validator("annotations")
    def validate_annotations(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        if value is not None:
            value = remove_null_keys(value)
        return value


class NamespacedMetadata(Metadata):
    namespace: str


class Resource(pydantic.BaseModel):
    apiVersion: str
    kind: str

    @classmethod
    def from_api(cls, res):
        return cls(**res.to_dict())


class Project(Resource):
    apiVersion: str = "project.openshift.io/v1"
    kind: str = "Project"
    metadata: Metadata


class Group(Resource):
    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Group"
    metadata: Metadata
    users: Optional[list[str]]

    @pydantic.validator("users")
    def validate_users(
        cls, value, values
    ):  # pylint: disable=unused-argument,no-self-argument
        return value if value else []


class User(Resource):
    apiVersion: str = "user.openshift.io/v1"
    kind: str = "User"
    metadata: Metadata
    fullName: Optional[str]
    groups: Optional[list[str]]
    identities: Optional[list[str]]


class identityUser(pydantic.BaseModel):
    name: Optional[str]
    uid: Optional[str]


class Identity(Resource):
    apiVersion: str = "user.openshift.io/v1"
    kind: str = "Identity"
    metadata: Metadata
    extra: Optional[dict[str, str]]
    providerName: str
    providerUserName: str
    user: Optional[identityUser]


class UserIdentityMapping(Resource):
    apiVersion: str = "user.openshift.io/v1"
    kind: str = "UserIdentityMapping"
    user: identityUser
    identity: identityUser


class RoleRef(pydantic.BaseModel):
    apiGroup: str
    kind: str
    name: str


class Subject(pydantic.BaseModel):
    kind: str
    namespace: Optional[str]
    name: str


class RoleBinding(Resource):
    apiVersion: str = "rbac.authorization.k8s.io/v1"
    kind: str = "RoleBinding"
    metadata: NamespacedMetadata
    roleRef: RoleRef
    subjects: list[Subject]


class RoleBindingList(Resource):
    apiVersion: str = "v1"
    kind: str = "List"
    items: list[RoleBinding]


class Response(pydantic.BaseModel):
    error: bool
    message: Optional[str]
    object: Optional[pydantic.BaseModel]


class HasRoleResult(pydantic.BaseModel):
    user: str
    project: str
    role: str
    has_role: bool
