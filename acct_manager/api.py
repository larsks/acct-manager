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

ADMIN_USERNAME = os.environ.get("ACCT_MGR_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ["ACCT_MGR_ADMIN_PASSWORD"]
IDENTITY_PROVIDER = os.environ["ACCT_MGR_IDENTITY_PROVIDER"]
AUTH_DISABLED = os.environ.get("ACCT_MGR_AUTH_DISABLED", "false").lower() == "true"
QUOTA_FILE = os.environ.get("ACCT_MGR_QUOTA_FILE", "quotas.json")

auth = flask_httpauth.HTTPBasicAuth()


def load_config():
    """Attempt to load the kubernetes config.

    First attempt to load the incluster configuration, and if that fails, try
    to load from the a kubeconfig file."""
    try:
        kubernetes.config.load_incluster_config()
    except kubernetes.config.ConfigException:
        kubernetes.config.load_kube_config()


def get_openshift_client():
    """Create and return an OpenShift API client"""
    load_config()
    k8s_client = kubernetes.client.api_client.ApiClient()
    return openshift.dynamic.DynamicClient(k8s_client)


def wrap_response(func):
    """Convert returned models to dictionaries.

    If an api functions returns something (such as an object from
    acct_manager.models) with a 'dict', call that to transform the object into
    a dictionary. Returning a dictionary will cause Flask to return a
    JSON response.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)

        if hasattr(res, "dict"):
            message = models.Response(
                error=False,
                object=res,
            )

            return message.dict(exclude_none=True)

        return res

    return wrapper


def handle_exceptions(func):
    """Transform exceptions into HTTP error messages"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except moc_openshift.NotFoundError:
            message = models.Response(error=True, message="object not found")
            return flask.Response(
                message.json(exclude_none=True), status=404, mimetype="application/json"
            )
        except exc.ValidationError as err:
            flask.current_app.logger.warning("validation error: %s", err)
            message = models.Response(error=True, message=f"validation error: {err}")
            return flask.Response(
                message.json(exclude_none=True), status=400, mimetype="application/json"
            )
        except exc.InvalidProjectError as err:
            # If the client attempts to operate on an invalid object (that is,
            # one without the required label), log a message but otherwise
            # treat it as a 404 error.
            flask.current_app.logger.warning(
                "attempt to operate on invalid object: %s", err.obj
            )
            message = models.Response(error=True, message="invalid project")
            return flask.Response(
                message.json(exclude_none=True), status=400, mimetype="application/json"
            )
        except exc.ConflictError:
            message = models.Response(error=True, message="object already exists")
            return flask.Response(
                message.json(exclude_none=True), status=409, mimetype="application/json"
            )
        except exc.AccountManagerError as err:
            flask.current_app.logger.warning("account manager errror: %s", err)
            message = models.Response(
                error=True,
                message=f"account manager API error: {err}",
            )
            return flask.Response(
                message.json(exclude_none=True), status=400, mimetype="application/json"
            )
        except exc.ApiException as err:
            flask.current_app.logger.error("kubernetes api error: %s", err)
            message = models.Response(
                error=True,
                message="Unexpected kubernetes API error",
            )
            return flask.Response(
                message.json(exclude_none=True), status=400, mimetype="application/json"
            )

    return wrapper


@auth.verify_password
def verify_password(username, password):
    """Validate user credentials.

    Return True when the request provides the appropriate username and password, or if
    AUTH_DISABLED is True. Return False otherwise.
    """

    return AUTH_DISABLED or (username == ADMIN_USERNAME and password == ADMIN_PASSWORD)


def create_app():
    """Create Flask application instance"""
    app = flask.Flask(__name__)
    openshift_client = get_openshift_client()
    moc = moc_openshift.MocOpenShift(
        openshift_client, IDENTITY_PROVIDER, QUOTA_FILE, app.logger
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
        return user

    @app.route("/users/<name>", methods=GET)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_user(name):
        user = moc.get_user(name)
        return user

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
        return project

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
        return models.HasRoleResult(
            user=user_name, project=project_name, role=role_name, has_role=res
        )

    @app.route(
        "/users/<user_name>/projects/<project_name>/roles/<role_name>", methods=PUT
    )
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def add_user_role(user_name, project_name, role_name):
        group = moc.add_user_to_role(user_name, project_name, role_name)
        return group

    @app.route(
        "/users/<user_name>/projects/<project_name>/roles/<role_name>", methods=DELETE
    )
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def delete_user_role(user_name, project_name, role_name):
        group = moc.remove_user_from_role(user_name, project_name, role_name)
        return group

    @app.route("/projects/<project_name>/quotas", methods=GET)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def get_quota(project_name):
        quotalist = moc.get_resourcequota(project_name)
        return quotalist

    @app.route("/projects/<project_name>/quotas", methods=PUT)
    @auth.login_required
    @handle_exceptions
    @wrap_response
    def update_quota(project_name):
        qreq = models.QuotaRequest(**flask.request.json)
        quotalist = moc.update_resourcequota(project_name, qreq.multiplier)
        return quotalist

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
