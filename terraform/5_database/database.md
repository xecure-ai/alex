# Alex Database Infrastructure (Terraform)

This document explains the Aurora Serverless v2 PostgreSQL stack defined in:
- `terraform/5_database/main.tf`
- `terraform/5_database/variables.tf`
- `terraform/5_database/outputs.tf`

## Overview
This module provisions an Amazon Aurora PostgreSQL-Compatible Serverless v2 cluster with a single serverless instance. It enables the RDS Data API to allow stateless access (ideal for Lambda) and manages DB credentials via AWS Secrets Manager. Networking is kept simple by using the default VPC and a dedicated security group.

## Components
- **Terraform backend and providers** (`main.tf`)
  - Terraform `>= 1.5`, providers: `hashicorp/aws ~> 5.0`, `hashicorp/random ~> 3.5`.
  - `provider "aws"` region is configurable via `var.aws_region`.

- **Random/Secrets** (`main.tf`)
  - `random_password.db_password` creates a 32-char password with specials.
  - `random_id.suffix` adds uniqueness to secret name.
  - `aws_secretsmanager_secret.db_credentials` stores DB credentials.
  - `aws_secretsmanager_secret_version.db_credentials` sets `username` and `password`.

- **Networking** (`main.tf`)
  - `data.aws_vpc.default` and `data.aws_subnets.default` select the default VPC and its subnets.
  - `aws_db_subnet_group.aurora` groups subnets for RDS.
  - `aws_security_group.aurora` allows PostgreSQL (5432) inbound from the VPC CIDR and all outbound.

- **Aurora cluster and instance** (`main.tf`)
  - `aws_rds_cluster.aurora` with:
    - `engine = aurora-postgresql`, `engine_version = 15.4`, `engine_mode = provisioned`.
    - Database name `alex`, master user `alexadmin`, password from Random.
    - Serverless v2 scaling via `serverlessv2_scaling_configuration { min_capacity = var.min_capacity, max_capacity = var.max_capacity }`.
    - `enable_http_endpoint = true` to enable Data API.
    - `db_subnet_group_name` and `vpc_security_group_ids` wired to resources above.
    - Backups and maintenance windows configured. Dev-friendly `skip_final_snapshot = true`, `apply_immediately = true`.
  - `aws_rds_cluster_instance.aurora` with `instance_class = db.serverless` and same engine/version.

- **IAM for Lambda + Data API** (`main.tf`)
  - `aws_iam_role.lambda_aurora_role` trust policy for `lambda.amazonaws.com`.
  - `aws_iam_role_policy.lambda_aurora_policy` permits:
    - `rds-data:*` (execute, batch, transaction ops) on the Aurora cluster ARN.
    - `secretsmanager:GetSecretValue` on the DB secret.
    - CloudWatch Logs creation and put events in the selected region/account.
  - `aws_iam_role_policy_attachment.lambda_basic` attaches `AWSLambdaBasicExecutionRole`.

## Variables
From `variables.tf`:
- `aws_region` (string): AWS region for resources.
- `min_capacity` (number, default `0.5` ACUs): Serverless v2 min capacity.
- `max_capacity` (number, default `1` ACU): Serverless v2 max capacity.

Notes:
- Aurora Serverless v2 ACU is a measure of capacity; billing scales between `min_capacity` and `max_capacity`.

## Outputs
From `outputs.tf`:
- `aurora_cluster_arn`: Cluster ARN.
- `aurora_cluster_endpoint`: Writer endpoint.
- `aurora_secret_arn`: Secrets Manager secret ARN.
- `database_name`: Database name (`alex`).
- `lambda_role_arn`: IAM role ARN for Lambda to access Aurora.
- `data_api_enabled`: Whether Data API is enabled (here: Enabled).
- `setup_instructions`: Post-deploy guidance, including `.env` entries and Data API test command.

## Security
- **Network**: SG allows 5432 from the VPC CIDR only; egress open to internet.
- **Credentials**: Stored in Secrets Manager. No plaintext passwords in Terraform outputs.
- **Least Privilege**: Inline policy limits `rds-data` to the specific cluster ARN and secrets access to the specific secret.
## Cost & Scaling
- Defaults set very low: `min_capacity = 0.5`, `max_capacity = 1` ACU.
- You can scale up `max_capacity` for higher throughput.
- To reduce spend in dev, consider lowering `min_capacity` to `0` to allow pausing after inactivity (see Output notes).

  ## How to Use
  - After apply, get values via `terraform output` or see `setup_instructions` output.
  - Suggested environment variables:
    - `AURORA_CLUSTER_ARN`
    - `AURORA_SECRET_ARN`
  - Test Data API:
  ```bash
  aws rds-data execute-statement \
    --resource-arn "$AURORA_CLUSTER_ARN" \
    --secret-arn "$AURORA_SECRET_ARN" \
    --database alex \
    --sql "SELECT version()"
  ```
    - Schema setup and test data (per `outputs.tf`):
  ```bash
  cd backend/database
  uv run migrate.py
  uv run reset_db.py --with-test-data
  ```

---
    
  ## Architecture Diagram
    ```mermaid
    graph TD
      subgraph AWS["VPC (default)"]
        SG["Security Group: aurora-sg<br/>Ingress: 5432 from VPC CIDR"]
        SUBNETS["DB Subnet Group: alex-aurora-subnet-group<br/>(default VPC subnets)"]
        RDS[("Aurora PostgreSQL Cluster<br/>engine: 15.4<br/>Serverless v2<br/>Data API Enabled")]
      end
      
      LAMBDA["AWS Lambda Functions<br/>(assume role: lambda_aurora_role)"]
      SM["Secrets Manager<br/>DB credentials"]
      CW[("CloudWatch Logs")]
    
      LAMBDA -->|GetSecretValue| SM
      LAMBDA -->|rds-data| RDS
      LAMBDA -->|logs:Put*| CW
      
      SG --> RDS
      SUBNETS --> RDS
    ```

  ## Data API Flow (Sequence)
  ```mermaid
  sequenceDiagram
    autonumber
    participant U as Caller (Lambda/App)
    participant SM as Secrets Manager
    participant RDS as Aurora Data API
    participant DB as Aurora Cluster
  
    U->>SM: GetSecretValue(AURORA_SECRET_ARN)
    SM-->>U: {username, password}
    U->>RDS: ExecuteStatement(resourceArn, secretArn, database, sql)
    RDS->>DB: Authenticate via secret, run SQL
    DB-->>RDS: Result set
    RDS-->>U: Rows/metadata
  ```

## Files and References
- Config: `terraform/5_database/main.tf`
- Variables: `terraform/5_database/variables.tf`
- Outputs & instructions: `terraform/5_database/outputs.tf`
## Notes & Tips
- Ensure `var.aws_region` matches your target region.
- The module uses the default VPC and all its subnets via `data.aws_subnets.default`.
- `skip_final_snapshot = true` is dev-friendly; for prod, consider enabling final snapshot and retention.
- Adjust maintenance and backup windows to your ops schedule.
