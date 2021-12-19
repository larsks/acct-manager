# MOC Account Management Microservice

## API specification

You can find the OpenAPI specification for this API in
[spec/openapi.yaml](spec/openapi.yaml). There is an HTML version of
the spec available at <http://oddbit.com/acct-manager/>.

## Running the code

 In the following instructions I'm assuming you're using [Code Ready
 Containers][crc]; if not, you may need to change the name of the
 identity provider.

### Running the code locally

This is generally the best option during development.

1. Make sure you're authenticated to your development OpenShift
   environment (with appropriate privileges for manipulating users,
   groups, rolebindings, etc).

   ```
   $ oc whoami
   kubeadmin
   ```

   [crc]: https://developers.redhat.com/products/codeready-containers/overview

2. Place the following content in a `.env` file in the current
   directory:

    ```
    ACCT_MGR_ADMIN_PASSWORD=secret
    ACCT_MGR_IDENTITY_PROVIDER=developer
    FLASK_ENV=development
    FLASK_APP=acct_manager.wsgi
    ```

3. Install package requirements:

    ```
    pip install -r requirements.txt
    ```

4. Run the code:

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
automatically when commits are pushed to this repository. You can run
the service with podman by doing something like this:

```
podman run --rm -p 8080:8080 \
  -v $HOME/.kube:/root/.kube \
  -v $PWD/manifests/onboarding-api/base/quotas.json:/data/quotas.json \
  --env-file .env \
  -e ACCT_MGR_QUOTA_FILE=/data/quotas.json \
  quay.io/larsks/moc-acct-manager:latest
```

As above, this requires you to be authenticated against OpenShift
because it uses your `~/.kube/config` file for credentials.

### Running the code in OpenShift

There are examples Kubernetes manifests in the `manifests` directory
that are designed to be applied using [Kustomize][]. To deploy this
application into [CRC][]:

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
the API service as described above, then set the
`ACCT_MGR_API_ENDPOINT` environment variable to the URL of the
service.

```
$ export ACCT_MGR_API_ENDPOINT=http://localhost:8080
$ pytest tests/functional
```

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
