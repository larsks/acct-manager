"""Implements the microservice REST API"""

import functools
import os

import flask
import flask_httpauth
import kubernetes
import openshift.dynamic

from . import moc_openshift
from . import models
from . import exc

GET = ["GET"]
POST = ["POST"]
DELETE = ["DELETE"]
PUT = ["PUT"]

DEFAULTS = {
    "ADMIN_USERNAME": "admin",
    "QUOTA_FILE": "quotas.json",
    "ENVVAR_PREFIX": "ACCT_MGR_",
}


def load_env_config(prefix):
    """Load configuration from environment variables"""

    config = {}
    for name, value in os.environ.items():
        if not name.startswith(prefix):
            continue

        name = name[len(prefix) :]
        config[name] = value

    return config


def load_kube_config():
    """Attempt to load the kubernetes config.

    First attempt to load the incluster configuration, and if that fails, try
    to load from the a kubeconfig file."""
    try:
        kubernetes.config.load_incluster_config()
    except kubernetes.config.ConfigException:
        kubernetes.config.load_kube_config()


def get_openshift_client():
    """Create and return an OpenShift API client"""
    load_kube_config()
    k8s_client = kubernetes.client.api_client.ApiClient()
    return openshift.dynamic.DynamicClient(k8s_client)


def wrap_response(func):
    """Convert returned models to dictionaries."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)

        if hasattr(res, "dict"):
            return res.dict(exclude_none=True)

        return res

    return wrapper


def handle_exceptions(func):
    """Transform exceptions into HTTP error messages"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        status = 400

        try:
            return func(*args, **kwargs)
        except moc_openshift.NotFoundError:
            message = models.Response(error=True, message="object not found")
            status = 404
        except (exc.ConflictError, exc.ObjectExistsError):
            message = models.Response(error=True, message="object already exists")
            status = 409
        except exc.InvalidProjectError as err:
            flask.current_app.logger.warning(
                "attempt to operate on invalid object: %s", err.obj
            )
            message = models.Response(error=True, message="invalid project")
            status = 403
        except exc.ValidationError as err:
            flask.current_app.logger.warning("validation error: %s", err)
            message = models.Response(error=True, message=f"validation error: {err}")
        except exc.AccountManagerError as err:
            flask.current_app.logger.warning("account manager errror: %s", err)
            message = models.Response(
                error=True,
                message=f"account manager API error: {err}",
            )
        except exc.ApiException as err:
            flask.current_app.logger.error("kubernetes api error: %s", err)
            message = models.Response(
                error=True,
                message="Unexpected kubernetes API error",
            )

        return flask.Response(
            message.json(exclude_none=True), status=status, mimetype="application/json"
        )

    return wrapper


# pylint: disable=too-many-locals
def create_app(**config):
    """Create Flask application instance"""

    openshift_client = get_openshift_client()

    auth = flask_httpauth.HTTPBasicAuth()
    app = flask.Flask(__name__)

    # Configure the application by reading config from:
    #
    # 1. The defaults
    # 2. Parameters passed to create_app
    # 3. The environment
    #
    # (Later settings override earlier ones)
    app.config.from_mapping(DEFAULTS)
    app.config.from_mapping(config)
    app.config.from_mapping(load_env_config(app.config["ENVVAR_PREFIX"]))

    moc = moc_openshift.MocOpenShift(
        openshift_client,
        app.config["IDENTITY_PROVIDER"],
        app.config["QUOTA_FILE"],
        app.logger,
    )

    @auth.verify_password
    def verify_password(username, password):
        """Validate user credentials.

        Return True when the request provides the appropriate username and password, or if
        AUTH_DISABLED is True. Return False otherwise.
        """

        return app.config.get("AUTH_DISABLED") or (
            username == app.config["ADMIN_USERNAME"]
            and password == app.config["ADMIN_PASSWORD"]
        )

    @app.route("/healthz", methods=GET)
    def healthcheck():
        """Healthcheck endpoint for asserting that service is running.

        Unlike all other methods, requests to this endpoint do not require
        authentication.
        """
        return flask.Response("OK", mimetype="text/plain")

    @app.route("/users", methods=POST)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def create_user():
        req = models.UserRequest(**flask.request.json)
        user = moc.create_user_bundle(req.name, req.fullName)
        return models.UserResponse(
            error=False,
            message=f"created user {user.metadata.name}",
            user=user,
        )

    @app.route("/users/<name>", methods=GET)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_user(name):
        user = moc.get_user(name)
        return models.UserResponse(
            error=False,
            message=f"user {user.metadata.name} exists",
            user=user,
        )

    @app.route("/users/<name>", methods=DELETE)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def delete_user(name):
        moc.delete_user_bundle(name)
        return models.Response(
            error=False,
            message=f"deleted user {name}",
        )

    @app.route("/projects", methods=POST)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def create_project():
        req = models.ProjectRequest(**flask.request.json)
        project = moc.create_project_bundle(
            req.name,
            req.requester,
            display_name=req.display_name,
            description=req.description,
        )
        return project

    @app.route("/projects/<name>", methods=GET)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_project(name):
        project = moc.get_project(name)
        return models.ProjectResponse(
            error=False,
            message=f"project {name} exists",
            project=project,
        )

    @app.route("/projects/<name>", methods=DELETE)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def delete_project(name):
        moc.delete_project_bundle(name)
        return models.Response(
            error=False,
            message=f"deleted project {name}",
        )

    @app.route(
        "/users/<user_name>/projects/<project_name>/roles/<role_name>", methods=GET
    )
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_user_role(user_name, project_name, role_name):
        res = moc.user_has_role(user_name, project_name, role_name)
        return models.RoleResponse(
            error=False,
            msg=f"role result for user {user_name} project {project_name} role {role_name}",
            role=models.RoleResponseData(
                user=user_name, project=project_name, role=role_name, has_role=res
            ),
        )

    @app.route(
        "/users/<user_name>/projects/<project_name>/roles/<role_name>", methods=PUT
    )
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def add_user_role(user_name, project_name, role_name):
        group = moc.add_user_to_role(user_name, project_name, role_name)
        return models.GroupResponse(
            error=False,
            msg=f"add user {user_name} to role {role_name} in project {project_name}",
            group=group,
        )

    @app.route(
        "/users/<user_name>/projects/<project_name>/roles/<role_name>", methods=DELETE
    )
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def delete_user_role(user_name, project_name, role_name):
        group = moc.remove_user_from_role(user_name, project_name, role_name)
        return models.GroupResponse(
            error=False,
            msg=f"remove user {user_name} from role {role_name} in project {project_name}",
            group=group,
        )

    @app.route("/projects/<project_name>/quotas", methods=GET)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_quota(project_name):
        quotalist = moc.get_resourcequota(project_name)
        return models.QuotaResponse(
            error=False,
            msg=f"quotas for project {project_name}",
            quotas=quotalist,
        )

    @app.route("/projects/<project_name>/quotas", methods=PUT)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def update_quota(project_name):
        qreq = models.QuotaRequest(**flask.request.json)
        quotalist = moc.update_resourcequota(project_name, qreq.multiplier)
        return models.QuotaResponse(
            error=False,
            msg=f"updated quotas for project {project_name}",
            quotas=quotalist,
        )

    @app.route("/projects/<project_name>/quotas", methods=DELETE)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def delete_quota(project_name):
        moc.delete_resourcequota(project_name)
        return models.Response(
            error=False, message=f"deleted quotas for project {project_name}"
        )

    return app
