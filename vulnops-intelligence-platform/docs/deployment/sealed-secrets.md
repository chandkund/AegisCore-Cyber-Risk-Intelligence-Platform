# Sealed Secrets workflow

[Bitnami Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) lets you store **encrypted** secret manifests in Git; only the in-cluster controller can decrypt them.

## When to use

- GitOps (Argo CD / Flux) without a cloud secret manager.  
- Complement to External Secrets when some values must remain in-repo as ciphertext.

## High-level flow

1. Install **Sealed Secrets controller** in `kube-system` (Helm or manifest).  
2. Install **`kubeseal`** CLI matching controller version.  
3. Fetch the cluster’s **certificate** for offline sealing (optional): `kubeseal --fetch-cert > cert.pem`.  
4. Generate `SealedSecret` from a **dry-run Secret** (see `infra/k8s/samples/README.md`).  
5. Apply `SealedSecret`; the controller creates the real `Secret` in the target namespace.

## Rotation

- Re-seal when credentials rotate; apply updated `SealedSecret` (controller updates the underlying `Secret`).  
- Document rotation in [credential rotation runbook](../runbooks/credential-rotation.md).

## Limitations

- **No** fine-grained RBAC on individual keys inside one SealedSecret — split secrets if teams need isolation.  
- Backup controller private key securely (disaster recovery).
