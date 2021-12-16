# MOC Onboarding Microservice API API Specification

The OpenAPI specification for this service is in
[openapi.yaml](openapi.yaml). You can find an HTML version of this
specification [here][].

[here]: http://oddbit.com/acct-manager

## Changes from original specification

This API has a few small changes vs. the specification on which it was
based.

 Previously, users were created via `PUT /users/<username>`. This
 follows the more common practice of using `POST /user` to create
 the new user object (with any necessary parameters provided in the
 request body).

 The same change has been made to the `/project` endpoint.
