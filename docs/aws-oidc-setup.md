# AWS OIDC Setup for the Backtest Workflow

This runbook replaces the legacy long-lived `AWS_ACCESS_KEY` / `AWS_SECRET_KEY`
repo secrets used by [`.github/workflows/aws-backtest.yml`](../.github/workflows/aws-backtest.yml)
with short-lived OIDC tokens issued per workflow run.

After completing this setup, the workflow assumes an IAM role via OIDC; no
static AWS credentials are stored in GitHub.

## Why OIDC over static keys

- **No long-lived credentials in GitHub.** Tokens are minted per workflow run
  and expire automatically.
- **Tighter blast radius.** The trust policy can be scoped to an exact branch,
  tag, or environment.
- **Auditability.** Every `AssumeRoleWithWebIdentity` call carries the
  triggering workflow and ref, visible in CloudTrail.
- **No rotation toil.** Nothing to rotate.

## Prerequisites

- AWS account with permission to create IAM identity providers and roles.
- AWS Batch queue + job definition the workflow already references
  (`vectorbt-queue` and `vectorbt-job-def` in `aws-backtest.yml`).
- Admin access to the GitHub repo (needed to add the role-ARN secret).

## Option A — Deploy the CloudFormation stack (recommended)

The template at [`infra/aws-oidc-github.yaml`](../infra/aws-oidc-github.yaml)
provisions everything in one stack:

1. The GitHub Actions OIDC identity provider (skipped if one already exists).
2. An IAM role scoped to a single sub-claim (`repo:OWNER/NQ-Backtest-Engine:ref:refs/heads/main`
   by default).
3. A least-privilege managed policy granting `batch:SubmitJob` on the
   referenced queue and job definition.

```bash
aws cloudformation deploy \
  --stack-name nq-backtest-oidc \
  --template-file infra/aws-oidc-github.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      GitHubOwner=YOUR_GITHUB_USERNAME \
      GitHubRepo=NQ-Backtest-Engine \
      AllowedRef=refs/heads/main \
      BatchJobQueueArn=arn:aws:batch:us-east-1:YOUR_ACCOUNT_ID:job-queue/vectorbt-queue \
      BatchJobDefinitionArn=arn:aws:batch:us-east-1:YOUR_ACCOUNT_ID:job-definition/vectorbt-job-def:1 \
      ResultsBucketName=your-backtest-results-bucket
```

If your account already has a GitHub OIDC provider (only one per account is
allowed), pass `CreateOidcProvider=false`.

Read the resulting role ARN out of the stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name nq-backtest-oidc \
  --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue" \
  --output text
```

Skip ahead to [Step 4](#step-4--add-the-role-arn-as-a-github-repo-secret).

## Option B — Manual setup via AWS CLI

### Step 1 — Create the OIDC identity provider

Skip this step if your account already has a provider for
`token.actions.githubusercontent.com` (only one per account is allowed).

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

> **About the thumbprint:** prior to July 2023, AWS required pinning the
> certificate thumbprint of GitHub's intermediate CA. AWS now validates
> GitHub's certificate chain against its own root CA bundle, so the
> `--thumbprint-list` argument is decorative and can be omitted on modern
> AWS CLI versions. The CloudFormation template still passes the legacy
> thumbprint values for backwards compatibility with older toolchains.

### Step 2 — Create the IAM role

Save the trust policy below as `trust-policy.json`, replacing
`YOUR_ACCOUNT_ID` and `YOUR_GITHUB_USERNAME`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/NQ-Backtest-Engine:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

> **Security note on `aud`.** The `aud` claim above is required. Without it,
> any audience that managed to obtain an OIDC token from GitHub could trade
> it for credentials in your account (a token-confusion attack). AWS docs
> require pinning `aud` to `sts.amazonaws.com` for this exact reason.

> **Scoping the `sub` claim.** The pattern above grants access only to runs
> on the `main` branch. Common alternatives:
> - Single PR / branch: `repo:OWNER/REPO:ref:refs/heads/feature-x`
> - Any tag: `repo:OWNER/REPO:ref:refs/tags/*` (use `StringLike` instead of `StringEquals`)
> - GitHub Environment (recommended for prod): `repo:OWNER/REPO:environment:prod`
>
> Reference: [GitHub docs — Configuring OpenID Connect in Amazon Web Services](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services).

Create the role:

```bash
aws iam create-role \
  --role-name github-actions-nq-backtest \
  --assume-role-policy-document file://trust-policy.json \
  --description "Assumed by GitHub Actions to submit NQ backtests to AWS Batch." \
  --max-session-duration 3600
```

### Step 3 — Attach the least-privilege permissions policy

The role needs two distinct grants: submitting Batch jobs, and reading/writing
backtest result artifacts in S3. Save as `permissions-policy.json` (substitute
your account ID, region, queue, job-definition revision, and bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SubmitBacktestJob",
      "Effect": "Allow",
      "Action": ["batch:SubmitJob"],
      "Resource": [
        "arn:aws:batch:us-east-1:YOUR_ACCOUNT_ID:job-queue/vectorbt-queue",
        "arn:aws:batch:us-east-1:YOUR_ACCOUNT_ID:job-definition/vectorbt-job-def:1"
      ]
    },
    {
      "Sid": "ReadBatchStatus",
      "Effect": "Allow",
      "Action": ["batch:DescribeJobs", "batch:ListJobs"],
      "Resource": "*"
    },
    {
      "Sid": "ReadWriteBacktestResults",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::your-backtest-results-bucket",
        "arn:aws:s3:::your-backtest-results-bucket/*"
      ]
    }
  ]
}
```

> **`ListBucket` lives on the bucket ARN, not the object ARN.** That's why
> the S3 statement has both forms in `Resource`. `PutObject` and `GetObject`
> need the `/*` form; `ListBucket` needs the bare bucket form.

> **Where the Batch *job* role fits in.** The role created here is assumed
> by the GitHub runner — it submits jobs and (optionally) uploads runner-side
> artifacts to S3. The container that AWS Batch runs uses a separate IAM
> role configured on the *job definition*. If your strategy code writes its
> own results to S3 from inside the container, mirror the
> `ReadWriteBacktestResults` statement onto that job role too. The
> CloudFormation template here does not manage the job role.

```bash
aws iam put-role-policy \
  --role-name github-actions-nq-backtest \
  --policy-name batch-submit-and-results \
  --policy-document file://permissions-policy.json
```

## Step 4 — Add the role ARN as a GitHub repo secret + bucket name as a variable

In the repo `Settings` -> `Secrets and variables` -> `Actions`:

1. **Secret** `AWS_BACKTEST_ROLE_ARN` — the role ARN from Step 2 / the
   `RoleArn` stack output (e.g.
   `arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-nq-backtest`).
2. **Variable** `RESULTS_BUCKET` — the S3 bucket where the Batch container
   writes its results (e.g. `your-backtest-results-bucket`). A *variable*,
   not a secret, because bucket names aren't sensitive and seeing them in
   logs is helpful for debugging.

While you're there, **delete the old static-credential secrets**:
`AWS_ACCESS_KEY` and `AWS_SECRET_KEY`.

## Step 5 — Workflow changes (already on `main` once this PR merges)

The relevant additions in [`.github/workflows/aws-backtest.yml`](../.github/workflows/aws-backtest.yml):

- `permissions.id-token: write` at job scope — required to mint the OIDC token.
- `aws-actions/configure-aws-credentials@v4` with `role-to-assume`, replacing
  the two access-key inputs.
- Inputs passed via `env:` (not interpolated into shell) to prevent
  script-injection on `inputs.strategy`.
- Polling loop on `aws batch describe-jobs` until terminal state, so the
  workflow's success/failure reflects the Batch job's outcome.
- `aws s3 cp` of `s3://${RESULTS_BUCKET}/runs/${run_id}/` followed by
  `actions/upload-artifact@v4` with `retention-days: 90` for traceability.
- `concurrency:` group keyed on the strategy input — same-strategy dispatches
  are serialized to avoid S3 prefix races.

## Step 6 — Verify

1. Run the workflow via `Actions` -> `AWS Backtest Run` -> `Run workflow`.
2. Watch the `Configure AWS Credentials` step — it should print
   `Authenticated as arn:aws:sts::...:assumed-role/github-actions-nq-backtest/...`.
3. In CloudTrail, look for an `AssumeRoleWithWebIdentity` event whose
   `requestParameters.providerId` ends in `token.actions.githubusercontent.com`
   and whose `userIdentity.sessionContext` shows the GitHub workflow run.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | `sub` claim doesn't match the trust policy | Print `${{ github.ref }}` in the workflow and confirm it matches `AllowedRef` exactly. PRs from forks have `sub=pull_request`, not `ref:refs/heads/...`. |
| `Could not load credentials from any providers` | `permissions: id-token: write` is missing | Add the `permissions` block at job or workflow level. |
| `An OIDC provider already exists for the same URL` | Stack tried to recreate the provider | Redeploy with `CreateOidcProvider=false`. |
| `OpenIDConnect provider's HTTPS certificate doesn't match configured thumbprint` | Toolchain is checking thumbprints against an old pin | Update to the current AWS CLI / `aws-actions/configure-aws-credentials@v4`; thumbprint pinning is no longer required. |

## References

- [GitHub Changelog — OIDC integration with AWS no longer requires pinning of intermediate TLS certificates](https://github.blog/changelog/2023-07-13-github-actions-oidc-integration-with-aws-no-longer-requires-pinning-of-intermediate-tls-certificates/) (Jul 2023)
- [GitHub Docs — Configuring OpenID Connect in AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [`aws-actions/configure-aws-credentials`](https://github.com/aws-actions/configure-aws-credentials) (v4)
