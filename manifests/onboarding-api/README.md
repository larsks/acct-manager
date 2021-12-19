# Deploy onboarding API

These manifests will deploy the onboarding API. To deploy the service
in [Code Ready Containers][crc]:

```
kustomize build overlays/crc | oc apply -f-
```

[crc]: https://developers.redhat.com/products/codeready-containers/overview
