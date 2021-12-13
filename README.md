# MOC Account Management Microservice

## Running the code locally

 In the following instructions I'm assuming you're using [Code Ready
 Containers][crc]; if not, you may need to change the name of the
 identity provider.

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

## Running the code in OpenShift

There are examples Kubernetes manifests in the `manifests` directory
that are designed to be applied using [Kustomize][]. To deploy this
application into [CRC][]:

[kustomize]: https://kustomize.io/

```
$ oc apply -k manifests/overlays/crc
```

That will deploy the following resources:

- An `onboarding` Namespace
- An `onboarding` ServiceAccount
- An `onboarding` Deployment
- An `onboarding-config` ConfigMap (with a hash suffix)
- An `onboarding` service
- An `onboarding` route (edge encrypted)
- A ClusterRoleBinding granting the `onboarding` ServiceAccount
  `cluster-admin` privileges

This uses the container image published at
`quay.io/larsks/moc-onboarding-api:latest`, which is rebuilt
automatically when commits are pushed to this repository.

## Unit tests

You can run the unit tests with `pytest`:

```
pytest tests/unit
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
Content-Length: 185
Content-Type: application/json
Date: Sun, 12 Dec 2021 22:22:13 GMT
Server: Werkzeug/2.0.2 Python/3.10.0

{
    "error": false,
    "object": {
        "apiVersion": "user.openshift.io/v1",
        "fullName": "test-user",
        "kind": "User",
        "metadata": {
            "name": "test-user"
        }
    }
}
```

## Delete a user

```
$ http --auth admin:secret DELETE localhost:8080/users/test-user
HTTP/1.0 200 OK
Content-Length: 102
Content-Type: application/json
Date: Sun, 12 Dec 2021 22:22:47 GMT
Server: Werkzeug/2.0.2 Python/3.10.0

{
    "error": false,
    "object": {
        "error": false,
        "message": "deleted user test-user"
    }
}
```

## Create a project

```
$ http --auth admin:secret localhost:8080/projects name=test-project requester=test-user
HTTP/1.0 200 OK
Content-Length: 320
Content-Type: application/json
Date: Sun, 12 Dec 2021 22:23:29 GMT
Server: Werkzeug/2.0.2 Python/3.10.0

{
    "error": false,
    "object": {
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
