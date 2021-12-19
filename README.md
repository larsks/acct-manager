# MOC Account Management Microservice

## API specification

You can find the OpenAPI specification for this API in
[spec/openapi.yaml](spec/openapi.yaml). There is an HTML version of
the spec available at <http://oddbit.com/acct-manager/>.

## Running the code in CRC

[Code Ready Containers][crc] allows you to quickly set up an OpenShift
development environment. This makes an excellent target for testing
out our onboarding API.

These instructions assume that you already have CRC running and that
the `oc` command is currently authenticated as the `kubeadmin` user.

[crc]: https://developers.redhat.com/products/codeready-containers/overview

### Configure CRC

First, apply the manifests in `manifests/authentication`:

```
oc apply -k manifests/authentication
```

This will create add a second identity provider (IDP) named
`onboarding` to your `OAuth` configuration. The IDP has three users
(`test-user-{1,2,3}`), all of which have the password `secret`, and is
configured in [`lookup` mode][lookup], which means that these users
will be unable to authenticate until you have created the necessary
`User`, `Identity`, and `UserIdentityMapping` objects in OpenShift
(e.g. by using the onboarding API).

[lookup]: https://docs.openshift.com/container-platform/4.9/authentication/understanding-identity-provider.html#identity-provider-parameters_understanding-identity-provider

This will also disable self-provisioning so that users are unable to
create new projects.

### Running the code locally

This is generally the best option during development.

1. Place the following content in a `.env` file in the current
   directory:

    ```
    ACCT_MGR_ADMIN_PASSWORD=secret
    ACCT_MGR_IDENTITY_PROVIDER=onboarding
    FLASK_ENV=development
    FLASK_APP=acct_manager.wsgi
    ```

1. Install package requirements:

    ```
    pip install -r requirements.txt
    ```

1. Run the code:

    ```
    flask run -p 8080
    ```

    Or if you prefer:

    ```
    gunicorn -b 127.0.0.1:8080 acct_manager.wsgi:app --log-file=-
    ```

### Running the code in a container

This repository is published as a container image at
`quay.io/larsks/moc-acct-manager:latest`, which is rebuilt
automatically when commits are pushed to this repository.

First, configure your `.env` file as in the previous section. You can
then run the service with podman by doing something like this:

```
podman run --rm -p 8080:8080 \
  -v $HOME/.kube:/root/.kube \
  -v $PWD/manifests/onboarding-api/base/quotas.json:/data/quotas.json \
  --env-file .env \
  -e ACCT_MGR_QUOTA_FILE=/data/quotas.json \
  quay.io/larsks/moc-acct-manager:latest
```

### Running the code in OpenShift

There are examples Kubernetes manifests in the
`manifests/onboarding-api` directory that are designed to be applied
using [Kustomize][]. To deploy this application into CRC:

[kustomize]: https://kustomize.io/

```
$ oc apply -k manifests/onboarding-api/overlays/crc
```

That will deploy the following resources:

- An `onboarding` Namespace
- An `onboarding` ServiceAccount
- An `onboarding` Deployment
- An `onboarding-config` ConfigMap (with a hash suffix)
- An `onboarding-credentials` Secret (with a hash suffix)
- An `onboarding` service
- An `onboarding` route (edge encrypted)
- A ClusterRoleBinding granting the `onboarding` ServiceAccount
  `cluster-admin` privileges

This uses the container image published at `quay.io/larsks/moc-acct-manager:latest`.

## Running the unit tests

You can run the unit tests with `pytest`:

```
pytest tests/unit
```

## Running the functional tests

The functional tests interact with a live version of the API. Start
the API service as described above, and then run the tests like this:

```
$ pytest tests/functional
```

By default the tests will attempt to interact with a service hosted at
`http://localhost:8080`. If you want to run the tests against a
different endpoint, you can set the `ACCT_MGR_API_ENDPOINT`
environment variable:

```
$ ACCT_MGR_API_ENDPOINT=https://onboarding-onboarding.apps-crc.testing \
  pytest tests/functional
```

These tests assume that you have deployed the `quotas.json` file in
this repository (which will be the case if you have deployed the
service using any of the mechanisms described in this document).

## Examples

You can interact with the service using `curl`, but your life will be
easier if you install [HTTPie][], which is what I'll be using in the
following examples.

[httpie]: https://httpie.io/cli

### Create a user

```
$ http --auth admin:secret localhost:8080/users name=test-user
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 223

{
  "error": false, 
  "message": "created user test-user", 
  "user": {
    "apiVersion": "user.openshift.io/v1", 
    "fullName": "test-user", 
    "kind": "User", 
    "metadata": {
      "name": "test-user"
    }
  }
}
```

### Delete a user

```
$ http --auth admin:secret DELETE localhost:8080/users/test-user
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 61

{
  "error": false, 
  "message": "deleted user test-user"
}
```

### Create a project

```
$ http --auth admin:secret localhost:8080/projects name=test-project requester=test-user
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 367

{
  "error": false, 
  "message": "created project test-project", 
  "project": {
    "apiVersion": "project.openshift.io/v1", 
    "kind": "Project", 
    "metadata": {
      "annotations": {
        "openshift.io/requester": "test-user"
      }, 
      "labels": {
        "massopen.cloud/project": "test-project"
      }, 
      "name": "test-project"
    }
  }
}
```

## See also

OpenShift documentation on quotas, limits, etc:

- "[Resource quotas per project][1]"
- "[Restrict resource consumption with limit ranges][2]"
- "[Configuring your cluster to place pods on overcommitted nodes][3]"
  (this is where the explanation of qos classes can be found)

[1]: https://docs.openshift.com/container-platform/4.9/applications/quotas/quotas-setting-per-project.html
[2]: https://docs.openshift.com/container-platform/4.9/nodes/clusters/nodes-cluster-limit-ranges.html
[3]: https://docs.openshift.com/container-platform/4.9/nodes/clusters/nodes-cluster-overcommit.html
