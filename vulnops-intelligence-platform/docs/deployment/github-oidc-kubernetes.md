# GitHub Actions OIDC → cloud → Kubernetes

Use **OpenID Connect** so workflows assume **short-lived** cloud roles instead of storing `KUBE_CONFIG` or static cloud keys.

## Pattern

1. Create an **OIDC identity provider** in the cloud that trusts GitHub’s issuer (`https://token.actions.githubusercontent.com`).  
2. Map **subject claims** (`repo:ORG/REPO:ref:refs/heads/main`, environment, etc.) to an **IAM role** / **workload identity**.  
3. Grant that role permission to **update EKS/AKS/GKE** or to pull **kubeconfig** via cloud API.  
4. In the workflow, grant `permissions: id-token: write` and call the cloud’s **login** action.

## AWS (EKS)

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/GitHubActionsVulnOpsDeploy
          aws-region: us-east-1
      - run: aws eks update-kubeconfig --name your-cluster --region us-east-1
      - run: kubectl apply -k infra/k8s/overlays/staging
```

**IAM role trust policy** (illustrative): `StringEquals` on `token.actions.githubusercontent.com:sub` for `repo:YOUR_ORG/vulnops-intelligence-platform:environment:staging`.

## Azure (AKS)

Use **`azure/login`** with **`client-id`**, **`tenant-id`**, **`subscription-id`**, and **`federated-credential`** configured on an app registration. Then `az aks get-credentials` and `kubectl apply`.

## Google Cloud (GKE)

Use **`google-github-actions/auth`** with **Workload Identity Federation** binding the GitHub repo to a GCP service account, then **`google-github-actions/get-gke-credentials`**.

## Hardening

- Scope **subject** to **environment** (`environment: production`) + **branch** restrictions.  
- Use **least privilege** on the cloud role (e.g. only `eks:DescribeCluster` + Kubernetes RBAC for deploy SA).  
- Prefer **per-environment** AWS roles / Azure federated credentials.

## Repository wiring

Workflows [deploy-staging.yml](../../.github/workflows/deploy-staging.yml) and [deploy-production.yml](../../.github/workflows/deploy-production.yml) include **optional** OIDC permission and commented **AWS** steps — uncomment and set **`AWS_DEPLOY_ROLE_ARN`** (or equivalent) after you create the role.
