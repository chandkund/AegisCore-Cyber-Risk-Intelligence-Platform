# Optional operator samples

These manifests assume third-party controllers are installed cluster-wide.

| File | Operator |
|------|----------|
| [external-secret-api.yaml](external-secret-api.yaml) | [External Secrets Operator](https://external-secrets.io/) — syncs `DATABASE_URL` and `JWT_SECRET_KEY` into `aegiscore-api-secret`. |

## Sealed Secrets (Bitnami)

Sealed Secrets encrypts a standard `Secret` into a `SealedSecret` CRD decryptable only by the cluster controller.

1. Install the controller and `kubeseal` CLI.  
2. Create a normal secret YAML (do not commit plaintext):

   ```bash
   kubectl -n aegiscore create secret generic aegiscore-api-secret \
     --from-literal=DATABASE_URL='...' \
     --from-literal=JWT_SECRET_KEY='...' \
     --dry-run=client -o yaml > /tmp/secret.yaml
   ```

3. Seal it:

   ```bash
   kubeseal -f /tmp/secret.yaml -w sealed-aegiscore-api-secret.yaml
   ```

4. Commit **`sealed-aegiscore-api-secret.yaml`** only; apply with `kubectl apply -f sealed-aegiscore-api-secret.yaml`.

See [sealed-secrets deployment doc](../../../docs/deployment/sealed-secrets.md).
