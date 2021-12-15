import re

from types import SimpleNamespace

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


def sanitize_project_name(name):
    """Make a project name match kubernetes naming requirements"""
    name = re.sub(r"[^\w]+", "-", name, flags=re.ASCII).lower()
    name = name.strip("-")
    return name


def check_role_name(name):
    """Check that the given role name is valid"""
    if name not in role_map:
        raise exc.InvalidRoleNameError(f"invalid role name: {name}")


def check_if_safe(obj):
    """Check if it's safe to delete or modify an object.

    We look for the massopen.cloud/project label, and if it doesn't exist,
    raise an InvalidProjectError."""
    if (
        obj.metadata.labels is None
        or "massopen.cloud/project" not in obj.metadata.labels
    ):
        raise exc.InvalidProjectError(obj=obj)


def make_group_name(project, role):
    """Create a group name for the given project and role"""
    return f"{project}-{role}"


def add_common_labels(obj, project_name):
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
    ]

    def __init__(self, api, identity_provider, quota_file, logger):
        self.api = api
        self.identity_provider = identity_provider
        self.quota_file = quota_file
        self.logger = logger
        self.setup_resource_apis()

    def setup_resource_apis(self):
        """Create API endpoints using the information in self.kinds"""
        self.resources = SimpleNamespace()
        for name, api_version, kind in self.kinds:
            setattr(
                self.resources,
                name,
                self.api.resources.get(api_version=api_version, kind=kind),
            )

    def qualify_user_name(self, name):
        """Qualify a username with the identity provider name"""
        return f"{self.identity_provider}:{name}"

    def get_project(self, name, unsafe=False):
        """Look up a project in OpenShift.

        Return a models.Project resource if it exists, otherwise raise a
        NotFoundError. If unsafe is False (the default), raise an
        InvalidProjectError if the specified project exists but does not have
        the required label."""
        res = self.resources.projects.get(name=name)
        project = models.Project.from_api(res)

        if not unsafe:
            check_if_safe(project)

        return project

    def project_exists(self, name):
        """Return True if the named project exists, False otherwise"""
        try:
            self.get_project(name, unsafe=True)
        except NotFoundError:
            return False
        else:
            return True

    def create_project(self, name, requester, display_name=None, description=None):
        """Create a new project"""
        self.logger.info("create project %s", name)
        if self.project_exists(name):
            raise exc.ProjectExistsError(f"project {name} already exists")
        project = models.Project(
            metadata=models.Metadata(
                name=name,
                annotations={
                    "openshift.io/display-name": display_name,
                    "openshift.io/description": description,
                    "openshift.io/requester": requester,
                },
            )
        )
        add_common_labels(project, name)

        self.resources.projects.create(body=project.dict(exclude_none=True))
        return project

    def delete_project(self, name):
        """Delete a project.

        This will raise an InvalidProjectError if an attempt is made to delete
        a project we didn't create."""
        self.logger.info("delete project %s", name)
        self.get_project(name)
        self.resources.projects.delete(name=name)

    def group_exists(self, name):
        """Return True if a group exists, False otherwise"""
        try:
            self.get_group(name, unsafe=True)
        except NotFoundError:
            return False
        else:
            return True

    def get_group(self, name, unsafe=False):
        """Look up a group in OpenShift.

        Return a models.Group resource if it exists, otherwise raise a
        NotFoundError. If unsafe is False (the default), raise an
        InvalidProjectError if the specified group exists but does not have
        the required label."""
        res = self.resources.groups.get(name=name)
        group = models.Group.from_api(res)

        if not unsafe:
            check_if_safe(group)

        return group

    def create_group(self, name, project_name):
        """Create a new group"""
        self.logger.info("create group %s", name)
        if self.group_exists(name):
            raise exc.GroupExistsError(f"group {name} already exists")

        group = models.Group(
            metadata=models.Metadata(
                name=name,
            ),
        )
        add_common_labels(group, project_name)
        self.resources.groups.create(body=group.dict(exclude_none=True))
        return group

    def delete_group(self, name):
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
        self, name, requester, display_name=None, description=None
    ):
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

        for role in role_map:
            group_name = f"{name}-{role}"
            self.create_group(group_name, name)
            self.create_rolebinding(name, group_name, role)

        return project

    def delete_project_bundle(self, name):
        """Delete a project and associated resources"""
        self.logger.info("delete project bundle for %s", name)

        for role in role_map:
            group_name = f"{name}-{role}"
            self.logger.debug("delete group %s", group_name)
            self.delete_group(group_name)

        self.delete_project(name)

    def user_exists(self, name):
        """Return True if a user exists, False otherwise"""
        try:
            self.get_user(name)
        except NotFoundError:
            return False
        else:
            return True

    def get_user(self, name):
        """Look up a user in OpenShift.

        Return a models.User resource if it exists, otherwise raise a
        NotFoundError."""
        res = self.resources.users.get(name=name)
        user = models.User.from_api(res)
        return user

    def create_user(self, name, full_name=None):
        """Create a new user"""
        self.logger.info("create user %s", name)
        user = models.User(
            metadata=models.Metadata(name=name),
            fullName=full_name if full_name else name,
        )

        self.resources.users.create(body=user.dict(exclude_none=True))
        return user

    def delete_user(self, name):
        """Delete a user"""
        self.logger.info("delete user %s", name)
        self.get_user(name)
        self.resources.users.delete(name=name)

    def create_rolebinding(self, project, group, role):
        """Create a rolebinding in a project binding a group to a role"""
        self.logger.info("create rolebinding for project %s role %s", project, role)
        check_role_name(role)
        rb_name = make_group_name(project, role)
        rb = models.RoleBinding(
            metadata=models.NamespacedMetadata(
                namespace=project,
                name=rb_name,
            ),
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

    def user_has_role(self, user, project, role):
        """Return True if the user has the given role in a project"""
        check_role_name(role)
        group_name = make_group_name(project, role)
        res = self.resources.groups.get(name=group_name)
        group = models.Group.from_api(res)
        try:
            return user in group.users
        except TypeError:
            return False

    def add_user_to_role(self, user, project, role):
        """Grant a user the named role in a project"""
        self.logger.info("add user %s to role %s in project %s", user, role, project)
        check_role_name(role)
        group_name = make_group_name(project, role)
        res = self.resources.groups.get(name=group_name)
        group = models.Group.from_api(res)

        if user not in group.users:
            group.users.append(user)
            self.resources.groups.patch(body=group.dict(exclude_none=True))

        return group

    def remove_user_from_role(self, user, project, role):
        """Revoke role for user in a project"""
        self.logger.info(
            "remove user %s from role %s in project %s", user, role, project
        )
        check_role_name(role)
        group_name = make_group_name(project, role)
        res = self.resources.groups.get(name=group_name)
        group = models.Group.from_api(res)

        # If group.users is None we have nothing to do
        try:
            group.users.remove(user)
        except ValueError:
            pass
        else:
            self.resources.groups.patch(body=group.dict(exclude_none=True))

        return group

    def get_identity(self, name):
        """Return an Identity for the given user.

        Raises a NotFoundError if the identity does not exist.
        """
        ident_name = self.qualify_user_name(name)
        res = self.resources.identities.get(name=ident_name)
        ident = models.Identity.from_api(res)
        return ident

    def create_identity(self, name):
        """Create a new identity for the given user.

        This creates an identity named {identity_provider}:{name} by
        calling self.qualify_name.
        """
        self.logger.info("create identity for %s", name)
        ident_name = self.qualify_user_name(name)
        ident = models.Identity(
            metadata=models.Metadata(name=ident_name),
            providerName=self.identity_provider,
            providerUserName=name,
        )
        self.resources.identities.create(body=ident.dict(exclude_none=True))
        return ident

    def identity_exists(self, name):
        """Return True if the given identity exists, False otherwise"""
        try:
            self.get_identity(name)
        except NotFoundError:
            return False
        else:
            return True

    def delete_identity(self, name):
        """Delete identity for the given user"""
        self.logger.info("delete identity for %s", name)
        id_name = self.qualify_user_name(name)
        if self.identity_exists(name):
            self.resources.identities.delete(name=id_name)

    def create_user_identity_mapping(self, name):
        """Create a new UserIdentityMapping for the given user"""
        self.logger.info("create identity mapping for %s", name)
        ident_name = self.qualify_user_name(name)
        mapping = models.UserIdentityMapping(
            user=models.identityUser(name=name),
            identity=models.identityUser(name=ident_name),
        )
        self.resources.useridentitymappings.create(body=mapping.dict(exclude_none=True))
        return mapping

    def create_user_bundle(self, name, full_name=None):
        """Create a user and associated resources.

        This will create:

        - The User itself
        - An Identity
        - A UserIdentityMapping associating the user with the identity
        """
        self.logger.info("create user bundle for %s", name)
        user = self.create_user(name, full_name=full_name)
        self.create_identity(name)
        self.create_user_identity_mapping(name)

        return user

    def remove_user_from_all_groups(self, name):
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

    def delete_user_bundle(self, name):
        """Delete a user and associated resources"""
        self.logger.info("delete user bundle for %s", name)
        self.delete_identity(name)
        self.remove_user_from_all_groups(name)
        self.delete_user(name)

    def read_quota_file(self):
        """Read quota definitions"""
        return models.QuotaFile.parse_file(self.quota_file)

    def get_resourcequota(self, project):
        """Get resourcequotas for a project"""
        self.logger.info("get resourcequotas in project %s", project)
        quotas = self.resources.resourcequotas.get(
            namespace=project, label_selector="massopen.cloud/project"
        )
        return models.ResourceQuotaList.from_api(quotas)

    def delete_resourcequota(self, project):
        """Delete all resourcequotas in a project"""
        self.logger.info("deleting resourcequotas in project %s", project)
        quotas = self.get_resourcequota(project)
        for quota in quotas.items:
            self.logger.debug(
                "deleting resourcequota %s from project %s",
                quota.metadata.name,
                project,
            )
            self.resources.resourcequotas.delete(
                name=quota.metadata.name, namespace=project
            )

    def generate_resourcequotas(self, project, multiplier):
        """Generate resourcequotas by applying multiplier to quota definition"""
        self.logger.info(
            "generating resourcequotas for project %s with multipler %d",
            project,
            multiplier,
        )
        quotafile = self.read_quota_file()
        quotas = models.ResourceQuotaList()
        for scope, spec in quotafile.dict().items():
            if spec is None:
                continue
            name = f"{project}-{scope}".lower()
            _scope = None if scope == "Project" else scope
            values = {}
            for qname, qvals in spec.items():
                value = qvals["base"] * qvals["coefficient"] * multiplier
                units = qvals["units"] if qvals["units"] else ""
                values[qname] = f"{value}{units}"
            r = models.ResourceQuota.from_quotaspec(name, project, _scope, values)
            quotas.items.append(r)

        return quotas

    def create_resourcequota(self, project, multiplier):
        """Create resourcequotas for a project"""
        self.logger.info(
            "creating resourcequotas for project %s with multiplier %d",
            project,
            multiplier,
        )
        quotas = self.generate_resourcequotas(project, multiplier)
        for quota in quotas.items:
            self.logger.debug(
                "creating resourcequota %s for project %s",
                quota.metadata.name,
                project,
            )
            self.resources.resourcequotas.create(body=quota.dict(exclude_none=True))

        return quotas

    def update_resourcequota(self, project, multiplier):
        """Delete and re-create quotas"""
        self.delete_resourcequota(project)
        return self.create_resourcequota(project, multiplier)
