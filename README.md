# NQ-Backtest-Engine
VectorBT-powered backtesting engine for NQ futures | Amazon Kiro optimized

## Documentation

- [AWS OIDC setup for the backtest workflow](docs/aws-oidc-setup.md) — replace
  long-lived `AWS_ACCESS_KEY` / `AWS_SECRET_KEY` secrets with role assumption
  via GitHub Actions OIDC. Includes a CloudFormation template at
  [`infra/aws-oidc-github.yaml`](infra/aws-oidc-github.yaml).
