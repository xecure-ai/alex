# Configuration Flow Between Guides

This document shows how configuration values flow between the different parts of the Alex project.

## Configuration Files

The project uses two types of configuration files:
- **`.env`** - Environment variables for Python scripts and backend services
- **`terraform.tfvars`** - Configuration for Terraform infrastructure deployments

Both are created from example files and are gitignored for security.

## Value Flow Diagram

```
Part 1: Initial Setup
├── AWS_ACCOUNT_ID ──────────────┬──> Part 3 (bucket naming)
└── DEFAULT_AWS_REGION ──────────┼──> Part 2 (Terraform)
                                 ├──> Part 3 (Terraform)
                                 ├──> Part 4 (Terraform)
                                 ├──> Part 5 (Terraform)
                                 └──> Part 6 (Terraform)

Part 2: SageMaker
└── SAGEMAKER_ENDPOINT ──────────> Part 3 (Lambda needs it)

Part 3: Ingestion
├── VECTOR_BUCKET ───────────────> Part 6 (Agents need it)
├── ALEX_API_ENDPOINT ───────────> Part 4 (Researcher uses it)
└── ALEX_API_KEY ────────────────> Part 4 (Researcher auth)

Part 4: Researcher
└── OPENAI_API_KEY ──────────────> (Used internally)
    Note: Researcher uses Bedrock OSS models in us-west-2

Part 5: Database
├── AURORA_CLUSTER_ARN ──────────> Part 6 (Agents need it)
└── AURORA_SECRET_ARN ───────────> Part 6 (Agents need it)

Part 6: Agents
├── BEDROCK_MODEL_ID ────────────> (Claude model configuration)
└── BEDROCK_REGION ──────────────> (us-west-2 has most models)
```

## Step-by-Step Configuration

### Part 1: Initial Setup
1. Copy `.env.example` to `.env`
2. Add your AWS_ACCOUNT_ID and DEFAULT_AWS_REGION

### Part 2: SageMaker
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Set aws_region (use your DEFAULT_AWS_REGION)
3. After deployment, add SAGEMAKER_ENDPOINT to `.env`

### Part 3: Ingestion
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Set aws_region and sagemaker_endpoint_name
3. After deployment, add to `.env`:
   - VECTOR_BUCKET
   - ALEX_API_ENDPOINT
   - ALEX_API_KEY

### Part 4: Researcher
1. Add OPENAI_API_KEY to `.env` (if not already there)
2. Copy `terraform.tfvars.example` to `terraform.tfvars`
3. Set all values from `.env`:
   - aws_region
   - openai_api_key
   - alex_api_endpoint (from Part 3)
   - alex_api_key (from Part 3)

### Part 5: Database
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Set aws_region, min_capacity, max_capacity
3. After deployment, add to `.env`:
   - AURORA_CLUSTER_ARN
   - AURORA_SECRET_ARN

### Part 6: Agents
1. Add to `.env`:
   - BEDROCK_MODEL_ID (e.g., anthropic.claude-4-sonnet-20250805-v1:0)
   - BEDROCK_REGION (typically us-west-2)
2. Copy `terraform.tfvars.example` to `terraform.tfvars`
3. Set all values from `.env`:
   - aws_region
   - aurora_cluster_arn (from Part 5)
   - aurora_secret_arn (from Part 5)
   - vector_bucket (from Part 3)
   - bedrock_model_id
   - bedrock_region

## Tips

### Viewing Terraform Outputs
After any Terraform deployment, you can view outputs with:
```bash
cd terraform/[part_directory]
terraform output
```

### Checking Your .env File
To see what values you've collected so far:
```bash
cat .env | grep -v "^#" | grep -v "^$"
```

### Getting Your AWS Account ID
```bash
aws sts get-caller-identity --query Account --output text
```

### Finding API Gateway Values
If you lose your API key ID, find it in the AWS Console:
1. Go to API Gateway
2. Select your API (alex-api)
3. Click "API Keys" in the left menu

Or use AWS CLI:
```bash
aws apigateway get-api-keys --query 'items[?name==`alex-api-key`].id' --output text
```

## Common Issues

### Missing Values
If Terraform complains about missing variables:
1. Check you copied the `.tfvars.example` file
2. Verify all values are filled in
3. Make sure there are no typos in variable names

### Region Considerations
- **DEFAULT_AWS_REGION**: Your main infrastructure region (used for SageMaker, Lambda, Aurora, etc.)
- **BEDROCK_REGION**: Should be us-west-2 (has most models)
- The OSS models in Part 4 (Researcher) are ONLY in us-west-2
- Claude models in Part 6 are best in us-west-2
- Cross-region calls work fine (e.g., Lambda in us-east-1 calling Bedrock in us-west-2)

### API Key Issues
The API key value is sensitive and only shown once. If you lose it:
1. Get the key ID from Terraform output
2. Use the AWS CLI command shown in the guide to retrieve it
3. Or create a new key in the AWS Console

## Complete .env Example

After completing all parts, your `.env` should look like:
```
# Part 1
AWS_ACCOUNT_ID=123456789012
DEFAULT_AWS_REGION=us-east-1

# Part 2
SAGEMAKER_ENDPOINT=alex-embedding-endpoint

# Part 3
VECTOR_BUCKET=alex-vectors-123456789012
ALEX_API_ENDPOINT=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/ingest
ALEX_API_KEY=abcdef123456

# Part 4
OPENAI_API_KEY=sk-...

# Part 5
AURORA_CLUSTER_ARN=arn:aws:rds:us-east-1:123456789012:cluster:alex-aurora-cluster
AURORA_SECRET_ARN=arn:aws:secretsmanager:us-east-1:123456789012:secret:alex-aurora-credentials-xxxxx

# Part 6
BEDROCK_MODEL_ID=anthropic.claude-4-sonnet-20250805-v1:0
BEDROCK_REGION=us-west-2
```