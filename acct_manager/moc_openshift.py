"""Python API for interesting with OpenShift"""
import logging
from types import SimpleNamespace
from typing import Any, Optional, Tuple, cast

# pylint: disable=unused-import
from kubernetes.client.exceptions import ApiException  # noqa: F401

# pylint: disable=unused-import
from openshift.dynamic.exceptions import NotFoundError, ConflictError  # noqa: F401

from . import models
from . import exc

role_map = {
    "admin": "admin",
    "member": "edit",
    "reader": "view",
}


def check_role_name(name: str) -> None:
    """Check that the given role name is valid"""
    if name not in role_map:
        raise exc.InvalidRoleNameError(f"invalid role name: {name}")


def check_if_safe(obj: models.Resource) -> None:
    """Check if it's safe to delete or modify an object.

    We look for the massopen.cloud/project label, and if it doesn't exist,
    raise an InvalidProjectError."""
    if (
        obj.metadata.labels is None
        or "massopen.cloud/project" not in obj.metadata.labels
    ):
        raise exc.InvalidProjectError(obj=obj)


def make_group_name(project: str, role: str) -> str:
    """Create a group name for the given project and role"""
    return f"{project}-{role}"


def add_common_labels(obj: models.Resource, project_name: str) -> None:
    """Add massopen.cloud/project label to object"""
    if obj.metadata.labels is None:
        obj.metadata.labels = {}

    obj.metadata.labels["massopen.cloud/project"] = project_name


# pylint: disable=too-many-public-methods
class MocOpenShift:
    """Backend API for the account management microservice"""

    # This list of tuples is used by setup_resource_apis to initialize our API
    # endpoints.
    kinds = [
        ("namespaces", "v1", "Namespace"),
        ("projects", "project.openshift.io/v1", "Project"),
        ("users", "user.openshift.io/v1", "User"),
        ("groups", "user.openshift.io/v1", "Group"),
        ("identities", "user.openshift.io/v1", "Identity"),
        ("useridentitymappings", "user.openshift.io/v1", "UserIdentityMapping"),
        ("rolebindings", "rbac.authorization.k8s.io/v1", "RoleBinding"),
        ("resourcequotas", "v1", "ResourceQuota"),
        ("limitranges", "v1", "LimitRange"),
    ]

    def __init__(
        self, api: Any, identity_provider: str, quota_file: str, logger: logging.Logger
    ) -> None:
        self.api = api
        self.identity_provider = identity_provider
        self.quota_file = quota_file
        self.quotas = models.QuotaFile(quotas=[], limits=[])
        self.logger = logger
        self.setup_resource_apis()

    def setup_resource_apis(self) -> None:
        """Create API endpoints using the information in self.kinds"""
        self.resources = SimpleNamespace()
        for name, api_version, kind in self.kinds:
            setattr(
                self.resources,
                name,
                self.api.resources.get(api_version=api_version, kind=kind),
            )

    def qualify_user_name(self, name: str) -> str:
        """Qualify a username with the identity provider name"""
        return f"{self.identity_provider}:{name}"

    def get_project(self, name: str, unsafe: bool = False) -> models.Project:
        """Look up a project in OpenShift.

        Return a models.Project resource if it exists, otherwise raise a
        NotFoundError. If unsafe is False (the default), raise an
        InvalidProjectError if the specified project exists but does not have
        the required label."""
        self.logger.info("look up project %s", name)
        res = self.resources.projects.get(name=name)
        project = models.Project.parse_obj(res)

        if not unsafe:
            check_if_safe(project)

        return project

    def project_exists(self, name: str) -> bool:
        """Return True if the named project exists, False otherwise"""
        try:
            self.get_project(name, unsafe=True)
        except NotFoundError:
            return False
        else:
            return True

    def create_project(
        self,
        name: str,
        requester: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> models.Project:
        """Create a new project"""
        self.logger.info("create project %s", name)
        if self.project_exists(name):
            raise exc.ProjectExistsError(f"project {name} already exists")
        project = models.Project.quick(
            name=name,
            annotations={
                "openshift.io/display-name": display_name,
                "openshift.io/description": description,
                "openshift.io/requester": requester,
            },
        )
        add_common_labels(project, name)

        self.resources.projects.create(body=project.dict(exclude_none=True))
        return project

    def delete_project(self, name: str) -> None:
        """Delete a project.

        This will raise an InvalidProjectError if an attempt is made to delete
        a project we didn't create."""
        self.logger.info("delete project %s", name)
        self.get_project(name)
        self.resources.projects.delete(name=name)

    def group_exists(self, name: str) -> bool:
        """Return True if a group exists, False otherwise"""
        try:
            self.get_group(name, unsafe=True)
        except NotFoundError:
            return False
        else:
            return True

    def get_group(self, name: str, unsafe: bool = False) -> models.Group:
        """Look up a group in OpenShift.

        Return a models.Group resource if it exists, otherwise raise a
        NotFoundError. If unsafe is False (the default), raise an
        InvalidProjectError if the specified group exists but does not have
        the required label."""
        res = self.resources.groups.get(name=name)
        group = models.Group.parse_obj(res)

        if not unsafe:
            check_if_safe(group)

        return group

    def get_role_group(self, project: str, role: str) -> models.Group:
        """Get group associated with a role on a project"""
        group_name = make_group_name(project, role)

        # check that role name is valid
        check_role_name(role)

        # check that we should be accessing the target project
        self.get_project(project)

        return self.get_group(group_name)

    def create_group(self, name: str, project_name: str) -> models.Group:
        """Create a new group"""
        self.logger.info("create group %s", name)
        if self.group_exists(name):
            raise exc.GroupExistsError(f"group {name} already exists")

        group = models.Group.quick(name=name)
        add_common_labels(group, project_name)
        self.resources.groups.create(body=group.dict(exclude_none=True))
        return group

    def delete_group(self, name: str) -> None:
        """Delete a group.

        This will raise an InvalidProjectError if an attempt is made to delete
        a group we didn't create."""
        self.logger.info("delete group %s", name)
        try:
            self.get_group(name)
            self.resources.groups.delete(name=name)
        except NotFoundError:
            pass

    def create_project_bundle(
        self,
        name: str,
        requester: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> models.Project:
        """Create a project and associated resources.

        This will create:

        - The project itself
        - A group for each role
        - A rolebinding binding each group the appropriate role
        """
        self.logger.info("create project bundle for %s", name)
        project = self.create_project(
            name, requester, display_name=display_name, description=description
        )

        try:
            for role in role_map:
                group_name = make_group_name(name, role)
                self.create_group(group_name, name)
                self.create_rolebinding(name, group_name, role)
        except Exception:
            self.logger.error(
                f"deleting project {name} due to failure creating groups or rolebinding"
            )
            self.delete_project_bundle(name)
            raise

        return project

    def delete_project_bundle(self, name: str) -> None:
        """Delete a project and associated resources"""
        self.logger.info("delete project bundle for %s", name)

        for role in role_map:
            group_name = make_group_name(name, role)
            self.logger.debug("delete group %s", group_name)
            self.delete_group(group_name)

        self.delete_project(name)

    def user_exists(self, name: str) -> bool:
        """Return True if a user exists, False otherwise"""
        try:
            self.get_user(name)
        except NotFoundError:
            return False
        else:
            return True

    def get_user(self, name: str) -> models.User:
        """Look up a user in OpenShift.

        Return a models.User resource if it exists, otherwise raise a
        NotFoundError."""
        res = self.resources.users.get(name=name)
        user = models.User.parse_obj(res)
        return user

    def create_user(self, name: str, full_name: Optional[str] = None) -> models.User:
        """Create a new user"""
        self.logger.info("create user %s", name)
        user = models.User.quick(name=name, fullName=full_name)

        self.resources.users.create(body=user.dict(exclude_none=True))
        return user

    def delete_user(self, name: str) -> None:
        """Delete a user"""
        self.logger.info("delete user %s", name)
        self.get_user(name)
        self.resources.users.delete(name=name)

    def create_rolebinding(
        self, project: str, group: str, role: str
    ) -> models.RoleBinding:
        """Create a rolebinding in a project binding a group to a role"""
        self.logger.info("create rolebinding for project %s role %s", project, role)
        check_role_name(role)
        rb_name = make_group_name(project, role)
        # pylint: disable=invalid-name
        rb = models.RoleBinding.quick(
            namespace=project,
            name=rb_name,
            roleRef=models.RoleRef(
                apiGroup="rbac.authorization.k8s.io",
                kind="ClusterRole",
                name=role_map[role],
            ),
            subjects=[
                models.Subject(
                    apiGroup="rbac.authorization.k8s.io",
                    kind="Group",
                    name=group,
                    namespace=project,
                )
            ],
        )
        self.resources.rolebindings.create(body=rb.dict(exclude_none=True))
        return rb

    def user_has_role(self, user: str, project: str, role: str) -> bool:
        """Return True if the user has the given role in a project"""
        self.logger.info(
            "check if user %s has role %s in project %s", user, role, project
        )
        group = self.get_role_group(project, role)
        return group.users is not None and user in group.users

    def add_user_to_role(self, user: str, project: str, role: str) -> models.Group:
        """Grant a user the named role in a project"""
        self.logger.info("add user %s to role %s in project %s", user, role, project)
        group = self.get_role_group(project, role)

        if group.users is not None and user not in group.users:
            group.users.append(user)
            self.resources.groups.patch(body=group.dict(exclude_none=True))

        return group

    def remove_user_from_role(self, user: str, project: str, role: str) -> models.Group:
        """Revoke role for user in a project"""
        self.logger.info(
            "remove user %s from role %s in project %s", user, role, project
        )
        group = self.get_role_group(project, role)

        try:
            if group.users is not None:
                group.users.remove(user)
                self.resources.groups.patch(body=group.dict(exclude_none=True))
        except ValueError:
            # .remove raises a ValueError if the given string is not in the
            # list (which means we don't need to make any changes).
            pass

        return group

    def get_identity(self, name: str) -> models.Identity:
        """Return an Identity for the given user.

        Raises a NotFoundError if the identity does not exist.
        """
        ident_name = self.qualify_user_name(name)
        res = self.resources.identities.get(name=ident_name)
        ident = models.Identity.parse_obj(res)
        return ident

    def create_identity(self, name: str) -> models.Identity:
        """Create a new identity for the given user.

        This creates an identity named {identity_provider}:{name} by
        calling self.qualify_name.
        """
        self.logger.info("create identity for %s", name)
        ident_name = self.qualify_user_name(name)
        ident = models.Identity.quick(
            name=ident_name,
            providerName=self.identity_provider,
            providerUserName=name,
        )

        self.resources.identities.create(body=ident.dict(exclude_none=True))
        return ident

    def identity_exists(self, name: str) -> bool:
        """Return True if the given identity exists, False otherwise"""
        try:
            self.get_identity(name)
        except NotFoundError:
            return False
        else:
            return True

    def delete_identity(self, name: str) -> None:
        """Delete identity for the given user"""
        self.logger.info("delete identity for %s", name)
        id_name = self.qualify_user_name(name)
        if self.identity_exists(name):
            self.resources.identities.delete(name=id_name)

    def create_user_identity_mapping(self, name: str) -> models.UserIdentityMapping:
        """Create a new UserIdentityMapping for the given user"""
        self.logger.info("create identity mapping for %s", name)
        ident_name = self.qualify_user_name(name)
        mapping = models.UserIdentityMapping.quick(
            name=ident_name,
            user=models.IdentityUser(name=name),
            identity=models.IdentityUser(name=ident_name),
        )
        self.resources.useridentitymappings.create(body=mapping.dict(exclude_none=True))
        return mapping

    def create_user_bundle(
        self, name: str, full_name: Optional[str] = None
    ) -> models.User:
        """Create a user and associated resources.

        This will create:

        - The User itself
        - An Identity
        - A UserIdentityMapping associating the user with the identity
        """
        self.logger.info("create user bundle for %s", name)

        user = self.create_user(name, full_name=full_name)

        try:
            self.create_identity(name)
            self.create_user_identity_mapping(name)
        except Exception:
            self.logger.error(
                f"deleting user {name} due to failure creating identity or mapping"
            )
            self.delete_user_bundle(name)
            raise

        return user

    def remove_user_from_all_groups(self, name: str) -> None:
        """Remove a user from all managed groups"""
        self.logger.info("removing user %s from all groups", name)
        groups = self.resources.groups.get(label_selector="massopen.cloud/project")
        for group in groups.items:
            group = models.Group(**dict(group))
            self.logger.debug(
                "removing user %s from group %s", name, group.metadata.name
            )
            try:
                group.users.remove(name)
            except (ValueError, AttributeError):
                pass
            else:
                self.resources.groups.patch(body=group.dict(exclude_none=True))

    def delete_user_bundle(self, name: str) -> None:
        """Delete a user and associated resources"""
        self.logger.info("delete user bundle for %s", name)
        self.delete_identity(name)
        self.remove_user_from_all_groups(name)
        self.delete_user(name)

    def read_quota_file(self) -> None:
        """Read quota definitions"""
        self.logger.info("reading quotas from %s", self.quota_file)
        try:
            with open(self.quota_file, "r", encoding="utf-8") as fd:
                self.quotas = models.QuotaFile.parse_raw(fd.read())
        except FileNotFoundError as err:
            self.logger.error("unable to read quota file %s: %s", self.quota_file, err)

    def get_limitrange(self, project: str) -> list[models.LimitRange]:
        """Get limitranges for a project"""
        self.logger.info("get limitranges in project %s", project)

        limitranges = self.resources.limitranges.get(
            namespace=project, label_selector="massopen.cloud/project"
        )
        return [models.LimitRange.parse_obj(item) for item in limitranges.items]

    def delete_limitrange(self, project: str) -> None:
        """delete all limitranges (that we created) in a project"""
        self.logger.info("deleting limitranges in project %s", project)
        limits = self.get_limitrange(project)
        for limit in limits:
            self.logger.debug(
                "deleting limitrange %s from project %s",
                limit.metadata.name,
                project,
            )
            self.resources.limitranges.delete(
                name=limit.metadata.name, namespace=project
            )

    def get_resourcequota(self, project: str) -> list[models.ResourceQuota]:
        """Get resourcequotas for a project"""
        self.logger.info("get resourcequotas in project %s", project)

        quotas = self.resources.resourcequotas.get(
            namespace=project, label_selector="massopen.cloud/project"
        )
        return [models.ResourceQuota.parse_obj(item) for item in quotas.items]

    def delete_resourcequota(self, project: str) -> None:
        """delete all resourcequotas (that we created) in a project"""
        self.logger.info("deleting resourcequotas in project %s", project)
        quotas = self.get_resourcequota(project)
        for quota in quotas:
            self.logger.debug(
                "deleting resourcequota %s from project %s",
                quota.metadata.name,
                project,
            )
            self.resources.resourcequotas.delete(
                name=quota.metadata.name, namespace=project
            )

    def generate_limitranges(self, project: str, multiplier: int) -> models.LimitRange:
        """Generate limitranges by applying multipllier to limit definition"""
        self.logger.info(
            "generating limitranges for project %s with multipler %d",
            project,
            multiplier,
        )

        all_limits: list[models.LimitDef] = []
        for limit in cast(list[models.QFLimitSpec], self.quotas.limits):
            limitdef = models.LimitDef(type=limit.type)
            for cat, values in dict(limit).items():
                if cat == "type":
                    continue
                if values is None:
                    continue

                resolved = {k: v.resolve(multiplier) for k, v in values.items()}
                setattr(limitdef, cat, resolved)
                all_limits.append(limitdef)

        return models.LimitRange.quick(
            name=f"{project}-limits",
            namespace=project,
            labels={"massopen.cloud/project": project},
            spec=models.LimitRangeSpec(
                limits=all_limits,
            ),
        )

    def generate_resourcequotas(
        self, project: str, multiplier: int
    ) -> list[models.ResourceQuota]:
        """Generate resourcequotas by applying multiplier to quota definition"""
        self.logger.info(
            "generating resourcequotas for project %s with multipler %d",
            project,
            multiplier,
        )

        resources = []
        for quota in cast(list[models.QFQuotaSpec], self.quotas.quotas):
            scopes = [
                scope.value for scope in quota.scopes if scope != models.Scope.Project
            ]
            combined = "-".join(scope.value for scope in quota.scopes)
            quotaname = f"{project}-quota-{combined}".lower()
            values = {}

            for name, valspec in quota.values.items():
                values[name] = valspec.resolve(multiplier)

            resources.append(
                models.ResourceQuota.quick(
                    name=quotaname,
                    namespace=project,
                    labels={"massopen.cloud/project": project},
                    spec=models.ResourceQuotaSpec(
                        scopes=scopes,
                        hard=values,
                    ),
                )
            )

        return resources

    def create_resourcequotas(
        self, project: str, multiplier: int
    ) -> list[models.ResourceQuota]:
        """Create resourcequotas for project"""

        self.logger.info(
            "creating resourcequotas for project %s with multiplier %d",
            project,
            multiplier,
        )

        quotas = self.generate_resourcequotas(project, multiplier)

        for quota in quotas:
            self.logger.debug(
                "creating resourcequota %s for project %s",
                quota.metadata.name,
                project,
            )
            self.resources.resourcequotas.create(body=quota.dict(exclude_none=True))

        return quotas

    def create_limitrange(
        self, project: str, multiplier: int
    ) -> list[models.LimitRange]:
        """Create limitranges for a project

        We only ever create a single limitrange, but we return a list to match
        the signature of create_resourcequotas."""

        self.logger.info(
            "creating limitrange for project %s with multiplier %d",
            project,
            multiplier,
        )

        limits = self.generate_limitranges(project, multiplier)
        self.resources.limitranges.create(body=limits.dict(exclude_none=True))

        return [limits]

    def create_quota_bundle(
        self, project: str, multiplier: int
    ) -> Tuple[list[models.ResourceQuota], list[models.LimitRange]]:
        """Create resourcequotas for a project"""

        self.logger.info(
            "create quota bundle for project %s with multiplier %d",
            project,
            multiplier,
        )

        # check that we should be accessing the target project
        self.get_project(project)

        # we re-read the quota file on each request in case there have been
        # changes.
        self.read_quota_file()

        if not self.quotas.quotas and not self.quotas.limits:
            raise exc.NoQuotasError("no quota is defined in configuration")

        quotas = self.create_resourcequotas(project, multiplier)
        limits = self.create_limitrange(project, multiplier)

        return quotas, limits

    def delete_quota_bundle(self, project: str) -> None:
        """Delete resourcequotas and limitranges in project"""

        self.logger.info("delete quota bundle for project %s", project)

        # check that we should be accessing the target project
        self.get_project(project)

        self.delete_resourcequota(project)
        self.delete_limitrange(project)

    def update_quota_bundle(
        self, project: str, multiplier: int
    ) -> Tuple[list[models.ResourceQuota], list[models.LimitRange]]:
        """Delete and re-create quotas"""
        self.delete_quota_bundle(project)
        return self.create_quota_bundle(project, multiplier)
