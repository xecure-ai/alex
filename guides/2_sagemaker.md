# Building Alex: Part 2 - SageMaker Serverless Deployment

Welcome back! In this guide, we'll deploy a SageMaker Serverless endpoint that will generate embeddings for Alex's knowledge base. This is a critical component - it converts text into numerical vectors that can be searched and compared.

## Why SageMaker?

We're using SageMaker for several important reasons:
1. **Production-ready**: Handles scaling, monitoring, and availability
2. **Cost-effective**: Serverless endpoints scale to zero when not in use
3. **Professional skill**: SageMaker is widely used in industry AI deployments

## What We're Building

We'll deploy:
- A SageMaker model that automatically downloads `all-MiniLM-L6-v2` from HuggingFace Hub
- A serverless endpoint that scales automatically
- Infrastructure as Code using Terraform

The beauty of this approach: no model preparation needed! SageMaker's HuggingFace container handles everything.

## Prerequisites

Before starting:
- Complete [1_permissions.md](1_permissions.md) 
- Have Terraform installed (version 1.5+)

## Step 1: Set Up Environment and State Storage

First, let's set up your AWS account ID as an environment variable and create the Terraform state bucket.

### Mac/Linux:
```bash
# Get and export your AWS account ID
export TF_VAR_aws_account_id=$(aws sts get-caller-identity --query Account --output text)

# Verify it's set
echo $TF_VAR_aws_account_id

# Create the state bucket (using your account ID for uniqueness)
# Note: Add --region parameter if you're not in us-east-1
aws s3api create-bucket \
  --bucket alex-terraform-state-${TF_VAR_aws_account_id}

# Enable versioning for safety
aws s3api put-bucket-versioning \
  --bucket alex-terraform-state-${TF_VAR_aws_account_id} \
  --versioning-configuration Status=Enabled
```

### Windows PowerShell:
```powershell
# Get and export your AWS account ID
$env:TF_VAR_aws_account_id = aws sts get-caller-identity --query Account --output text

# Verify it's set
echo $env:TF_VAR_aws_account_id

# Create the state bucket (using your account ID for uniqueness)
# Note: Add --region parameter if you're not in us-east-1
aws s3api create-bucket --bucket "alex-terraform-state-$env:TF_VAR_aws_account_id"

# Enable versioning for safety
aws s3api put-bucket-versioning --bucket "alex-terraform-state-$env:TF_VAR_aws_account_id" --versioning-configuration Status=Enabled
```

**Important**: The `TF_VAR_` prefix tells Terraform to use this as a variable. Keep this terminal/PowerShell window open throughout the deployment!

## Step 2: Deploy with Terraform

Now let's deploy the SageMaker infrastructure. With the HuggingFace approach, there's no need to prepare model artifacts - the model will be downloaded automatically from HuggingFace Hub!

```bash
# Navigate to terraform directory
cd terraform

# Set your AWS region (if not already set)
export AWS_DEFAULT_REGION=$(aws configure get region)

# Initialize Terraform with your state bucket
# Mac/Linux:
terraform init \
  -backend-config="bucket=alex-terraform-state-${TF_VAR_aws_account_id}" \
  -backend-config="key=production/terraform.tfstate"

# Windows PowerShell:
$env:AWS_DEFAULT_REGION = aws configure get region
terraform init `
  -backend-config="bucket=alex-terraform-state-$env:TF_VAR_aws_account_id" `
  -backend-config="key=production/terraform.tfstate"

# Deploy ONLY the SageMaker infrastructure
# We use -target to avoid needing other variables yet
terraform apply \
  -target=aws_iam_role.sagemaker_role \
  -target=aws_iam_role_policy_attachment.sagemaker_full_access \
  -target=aws_sagemaker_model.embedding_model \
  -target=aws_sagemaker_endpoint_configuration.serverless_config \
  -target=aws_sagemaker_endpoint.embedding_endpoint
```

**Note**: We're using `-target` to deploy only SageMaker resources for now. If prompted for any other variables, just press Enter to use defaults - they won't be used yet.

When prompted, type `yes` to confirm. This will create:
- IAM role for SageMaker
- SageMaker model configuration (with HuggingFace model ID)
- Serverless endpoint

## Step 3: Understanding What Was Created

Terraform created several resources:

1. **IAM Role**: Gives SageMaker permissions it needs
2. **SageMaker Model**: Configuration pointing to HuggingFace model `sentence-transformers/all-MiniLM-L6-v2`
3. **Serverless Endpoint**: The API endpoint for generating embeddings

After deployment, you'll see outputs like:
```
sagemaker_endpoint_name = "alex-embedding-endpoint"
sagemaker_role_arn = "arn:aws:iam::YOUR_ACCOUNT_ID:role/alex-sagemaker-execution-role"
```

Save the `sagemaker_endpoint_name` - you'll need it for the Lambda function.

## Step 4: Test the Endpoint

Let's verify the endpoint works with a simple test:

```bash
# Navigate to backend directory where test payload is located
cd ../backend

# Invoke the endpoint and output directly to console
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name alex-embedding-endpoint \
  --content-type application/json \
  --body fileb://vectorize_me.json \
  --output json \
  /dev/stdout
```

You'll see a JSON array with 384 floating-point numbers - that's the text "vectorize me" converted into a vector embedding!

**Note**: The first request to a serverless endpoint can take 10-60 seconds (cold start). Subsequent requests will be much faster.

## Cost Analysis

Your serverless endpoint:
- **Scales to zero**: No charges when not in use
- **Request pricing**: ~$0.00002 per second of compute
- **Memory**: 3GB allocated (AWS default limit for serverless)
- **Estimated cost**: $1-2/month for typical usage (1000 requests/day)

## Troubleshooting

If the endpoint invocation fails:

1. **Check endpoint status**:
```bash
aws sagemaker describe-endpoint --endpoint-name alex-embedding-endpoint
```
Status should be "InService"

2. **Check CloudWatch logs**:
```bash
aws logs tail /aws/sagemaker/Endpoints/alex-embedding-endpoint --follow
```

3. **Verify the HuggingFace model ID**:
Check that the endpoint is configured with the correct model:
```bash
aws sagemaker describe-model --model-name alex-embedding-model --query 'PrimaryContainer.Environment'
```
Should show: `{"HF_MODEL_ID": "sentence-transformers/all-MiniLM-L6-v2", "HF_TASK": "feature-extraction"}`

**Note**: If you're not in the default region, add `--region your-region` to these commands.

## Understanding Serverless vs Always-On

We chose serverless because:
- **Cold starts**: 5-10 seconds (acceptable for our use case)
- **Cost savings**: ~$1-2/month vs $50-100/month for always-on
- **Auto-scaling**: Handles traffic spikes automatically

For production systems with strict latency requirements, you might choose always-on endpoints.

## Clean Up (Optional)

If you need to tear down the infrastructure:

```bash
cd terraform
terraform destroy
```

⚠️ Only do this if you want to remove everything!

## Next Steps

Congratulations! You've deployed a production-grade ML model on AWS. 

In the next guide, we'll:
1. Set up S3 Vectors for cost-effective vector storage (90% cheaper!)
2. Create a Lambda function to connect everything
3. Build an API for ingesting financial knowledge

Your SageMaker endpoint is ready and waiting. Let's continue building Alex! 🎉

Continue to: [3_ingest.md](3_ingest.md)