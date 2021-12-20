# Configure authentication

These manifests will:

1. Disable self-provisioning so that new users cannot create projects.

2. Configure a second htpasswd-style identity provider named
   `onboarding`, and provision three users (`test-user-{1,2,3}`), all
   with the password `secret`. The idp is configured in `lookup` mode,
   which means the users will not be able to authenticate until you
   create the necessary users, identities, and mappings (e.g. by using
   the onboarding API).
