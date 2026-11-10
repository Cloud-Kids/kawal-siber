# 17. AWS OIDC Identity Provider & IAM Setup

## 1. Setup GitHub OIDC Identity Provider in AWS

Execute using the AWS CLI or CloudFormation:

```bash
# 1. Create the GitHub Actions OIDC Identity Provider
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c58761f274dfe829fac8ebd6e18143294c14f02"
```

---

## 2. Create the IAM Deployment Role & Trust Policy

### 2.1 Trust Policy (`github-oidc-trust-policy.json`)
Replace `123456789012` with your AWS Account ID and `OWNER/KAWAL-SIBER` with your GitHub repository path:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubOIDCAuth",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
            "repo:OWNER/KAWAL-SIBER:ref:refs/heads/main",
            "repo:OWNER/KAWAL-SIBER:environment:production"
          ]
        }
      }
    }
  ]
}
```

### 2.2 Create the IAM Role via CLI
```bash
aws iam create-role \
  --role-name "kawal-siber-github-deployer-role" \
  --assume-role-policy-document file://infra/aws/iam/github-oidc-trust-policy.json \
  --description "Least-privilege role assumed by GitHub Actions for KAWAL SIBER production deployment"
```

### 2.3 Attach the Deployment Policy
```bash
aws iam put-role-policy \
  --role-name "kawal-siber-github-deployer-role" \
  --policy-name "kawal-siber-deployer-permissions" \
  --policy-document file://infra/aws/iam/github-deployer-policy.json
```

---

## 3. Verification of OIDC Authentication

Verify that the role can be assumed only by authenticated GitHub Actions runs matching the repository and branch:
```bash
aws sts get-caller-identity
```
In GitHub Actions workflow:
```yaml
- name: Configure AWS credentials via OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
    aws-region: ap-southeast-1
    audience: sts.amazonaws.com
```

