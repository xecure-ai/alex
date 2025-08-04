# Building Alex: Part 3 - OpenSearch Serverless and Lambda

Welcome back! In this final infrastructure guide, we'll deploy the complete Alex backend:
- OpenSearch Serverless for vector storage
- Lambda function for document ingestion  
- API Gateway with API key authentication
- Integration with the SageMaker embedding endpoint

## Prerequisites
- Completed [Guide 1](1_permissions.md) (AWS setup - **including the OpenSearch Serverless custom policy**)
- Completed [Guide 2](2_sagemaker.md) (SageMaker deployment)
- AWS CLI configured
- Terraform installed
- Python with `uv` package manager installed

⚠️ **Important**: If you get "AccessDeniedException" errors for OpenSearch Serverless (aoss), make sure you completed steps 1.3 and 1.4 in Guide 1 to create and attach the custom OpenSearch Serverless policy.

## Step 1: Prepare the Lambda Deployment Package

The Lambda function code is already in the repository. We just need to create the deployment package:

```bash
# Navigate to the ingest directory
cd backend/ingest

# Install dependencies and create deployment package
uv run package.py
```

This creates `lambda_function.zip` containing your function and all dependencies. You should see output like:
```
✅ Deployment package created: lambda_function.zip
   Size: ~15 MB
```

## Step 2: Deploy the Infrastructure

First, ensure your AWS account ID environment variable is set (from Guide 2):

### Mac/Linux:
```bash
# If not already set from Guide 2
export TF_VAR_aws_account_id=$(aws sts get-caller-identity --query Account --output text)

# Verify it's set
echo $TF_VAR_aws_account_id
```

### Windows PowerShell:
```powershell
# If not already set from Guide 2
$env:TF_VAR_aws_account_id = aws sts get-caller-identity --query Account --output text

# Verify it's set
echo $env:TF_VAR_aws_account_id
```

Navigate to the Terraform directory:
```bash
cd ../../terraform
```

If you're continuing from Guide 2 in the same session, Terraform is already initialized. Otherwise, initialize it:

### Mac/Linux:
```bash
terraform init \
  -backend-config="bucket=alex-terraform-state-${TF_VAR_aws_account_id}" \
  -backend-config="key=production/terraform.tfstate" \
  -backend-config="region=us-east-1"
```

### Windows PowerShell:
```powershell
terraform init `
  -backend-config="bucket=alex-terraform-state-$env:TF_VAR_aws_account_id" `
  -backend-config="key=production/terraform.tfstate" `
  -backend-config="region=us-east-1"
```

Plan the deployment to see what will be created:
```bash
terraform plan
```

You should see resources for:
- OpenSearch Serverless collection and policies
- Lambda function and IAM role
- API Gateway REST API with API key

Deploy the infrastructure:
```bash
terraform apply
```

Type `yes` when prompted to confirm.

⏱️ **Note**: The OpenSearch Serverless collection will take 5-10 minutes to create. You'll see "Still creating..." messages - this is normal. OpenSearch Serverless needs time to provision the infrastructure.

## Step 3: Wait for OpenSearch to Initialize

OpenSearch Serverless collections take 5-10 minutes to become active. You can check the status in the AWS Console:
1. Go to OpenSearch Service
2. Click on "Serverless" in the left menu
3. Find your "alex-portfolio" collection
4. Wait for the status to show "Active"

## Step 4: Save Your Configuration

Let's save the important values to your `.env` file for use in Python scripts and future development.

### Mac/Linux:
```bash
# Navigate to project root
cd ..

# Add API configuration to .env file
echo "" >> .env
echo "# Alex API Configuration" >> .env
echo "ALEX_API_ENDPOINT=$(terraform -chdir=terraform output -raw api_endpoint)" >> .env
echo "ALEX_API_KEY=$(terraform -chdir=terraform output -raw api_key_value)" >> .env
echo "AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)" >> .env

# Also save OpenSearch and SageMaker endpoints for direct access if needed
echo "OPENSEARCH_ENDPOINT=$(terraform -chdir=terraform output -raw opensearch_endpoint)" >> .env
echo "SAGEMAKER_ENDPOINT=$(terraform -chdir=terraform output -raw sagemaker_endpoint_name)" >> .env

# Verify the values were added
tail -n 6 .env
```

### Windows PowerShell:
```powershell
# Navigate to project root
cd ..

# Get the values
$api_endpoint = terraform -chdir=terraform output -raw api_endpoint
$api_key = terraform -chdir=terraform output -raw api_key_value
$account_id = aws sts get-caller-identity --query Account --output text
$opensearch = terraform -chdir=terraform output -raw opensearch_endpoint
$sagemaker = terraform -chdir=terraform output -raw sagemaker_endpoint_name

# Append to .env file
Add-Content .env ""
Add-Content .env "# Alex API Configuration"
Add-Content .env "ALEX_API_ENDPOINT=$api_endpoint"
Add-Content .env "ALEX_API_KEY=$api_key"
Add-Content .env "AWS_ACCOUNT_ID=$account_id"
Add-Content .env "OPENSEARCH_ENDPOINT=$opensearch"
Add-Content .env "SAGEMAKER_ENDPOINT=$sagemaker"

# Verify the values were added
Get-Content .env -Tail 7
```

These environment variables will be available for:
- Python scripts that interact with your API
- Jupyter notebooks for analysis
- Frontend applications
- Testing and debugging

## Step 5: Test the Deployment

We've included a Python test script that loads multiple documents into your knowledge base:

```bash
# Navigate to the ingest directory where the Python project is
cd backend/ingest

# Run the test script (dependencies are already in pyproject.toml)
uv run test_api.py
```

This script will:
- Load your API configuration from the `.env` file
- Ingest several sample stock documents
- Verify each document is indexed successfully
- Automatically retry if the first request fails (common with serverless cold starts)

**Note**: The first request might fail or take longer (10-30 seconds) due to SageMaker Serverless cold start. This is normal - subsequent requests will be much faster.

You should see output like:
```
Testing Alex API...
Endpoint: https://your-api-id.execute-api.us-east-1.amazonaws.com/prod

Ingesting document 1: TSLA
  ✓ Success! Document ID: 1%3A0%3A...
  
Ingesting document 2: AMZN
  ✓ Success! Document ID: 1%3A0%3A...

Ingesting document 3: NVDA
  ✓ Success! Document ID: 1%3A0%3A...

Testing complete!

Your Alex knowledge base now contains information about:
  - Tesla Inc. (TSLA)
  - Amazon.com Inc. (AMZN)
  - NVIDIA Corporation (NVDA)
```

## Step 6: Explore Your OpenSearch Database

You can explore your data in two ways:

### Option A: Using the Python Script (Recommended)

```bash
# Still in backend/ingest directory
uv run search_api.py
```

**Note**: If you get an "AuthorizationException(403)" error, wait 1-2 minutes for the OpenSearch access policy to propagate, then try again. This is normal when first deploying.

This will show you:
- How many documents are indexed
- Details of each document (ticker, company, text preview)
- Example text searches across your knowledge base

### Option B: Using the AWS Console

1. Go to the AWS Console and navigate to **Amazon OpenSearch Service**
2. Click on **Serverless** in the left sidebar
3. Click on your collection **alex-portfolio**
4. Click the **OpenSearch Dashboards URL** link at the top
5. In OpenSearch Dashboards:
   - Click the hamburger menu (☰) in the top left
   - Go to **Management** → **Dev Tools**
   - Try these queries:

```json
// List all documents
GET alex-knowledge/_search
{
  "query": {"match_all": {}},
  "_source": {"excludes": ["embedding"]}
}

// Search for specific terms
GET alex-knowledge/_search
{
  "query": {"match": {"text": "cloud computing"}},
  "_source": {"excludes": ["embedding"]}
}

// Count documents
GET alex-knowledge/_count
```

The Console gives you a full OpenSearch Dashboards interface where you can:
- Run queries
- View mappings
- Create visualizations
- Monitor performance

You should see output like:
```
Alex OpenSearch Database Explorer
============================================================
✓ Index 'alex-knowledge' exists with 3 documents

Found 3 documents in OpenSearch:

1. Document ID: 1%3A0%3A...
   Ticker: TSLA
   Company: Tesla Inc.
   Sector: Automotive/Energy
   Text: Tesla Inc. (TSLA) is an electric vehicle and clean energy company...
   
2. Document ID: 1%3A0%3A...
   Ticker: AMZN
   Company: Amazon.com Inc.
   Sector: Technology/Retail
   Text: Amazon.com Inc. (AMZN) is a multinational technology company...
```

## Step 7: Available Management Scripts

You now have three Python scripts to manage your Alex knowledge base:

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_api.py` | Add sample stock data | `uv run test_api.py` |
| `search_api.py` | Explore and search your data | `uv run search_api.py` |
| `cleanup_api.py` | Reset/clear your database | `uv run cleanup_api.py` |

All scripts should be run from the `backend/ingest` directory.

**Important**: OpenSearch Serverless has eventual consistency. After adding documents with `test_api.py`, wait 5-10 seconds before running `search_api.py` to ensure the documents are searchable.

## Step 8: Verify in CloudWatch (Optional)

For debugging, check your Lambda logs:
1. Go to CloudWatch in AWS Console
2. Navigate to Log groups
3. Find `/aws/lambda/alex-ingest`
4. Check the latest log stream for execution details

## Troubleshooting

### Lambda Timeout
If you get timeout errors, the Lambda function might need more time:
- Edit `terraform/modules/lambda/main.tf`
- Increase the `timeout` value (e.g., to 60 seconds)
- Run `terraform apply` again

### OpenSearch Access Denied
If you get access denied errors:
1. Ensure the OpenSearch collection is Active
2. Check the IAM policies in the Lambda role
3. Verify the OpenSearch access policy includes your Lambda role

### API Gateway 403 Forbidden
If you get 403 errors:
- Ensure you're including the `x-api-key` header
- Verify the API key is correct
- Check that the usage plan is attached to your API key

### Resetting Your Database
If you want to start fresh or clean up test data:

```bash
# In backend/ingest directory
uv run cleanup_api.py
```

This interactive script lets you:
- Delete all documents (keeping the index structure)
- Delete the entire index (complete reset)
- See how many documents are currently stored

Use this when you want to:
- Clear out test data before adding real data
- Fix issues with corrupted documents
- Start over with a clean database

### Important Note: Terraform Destroy
If you ever run `terraform destroy` and then `terraform apply` again, your OpenSearch collection will be recreated with a new endpoint URL. You'll need to update the `.env` file:

```bash
cd terraform
echo "OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)" >> ../.env
```

Then manually edit `.env` to remove the old OPENSEARCH_ENDPOINT line. This is only necessary if you destroy and recreate the infrastructure.

## Cost Considerations

This deployment includes:
- **OpenSearch Serverless**: ~$0.24/hour when active (minimum billing)
- **Lambda**: Pay per invocation (very low cost for testing)
- **API Gateway**: $3.50 per million requests
- **SageMaker Serverless**: $0.008 per inference request

**Important**: OpenSearch Serverless has a minimum charge even with no data. Delete the stack when not in use:
```bash
terraform destroy
```

## Next Steps

Your Alex backend is now fully deployed! You can:
1. Start ingesting portfolio data through the API
2. Build a frontend to interact with your API
3. Add more sophisticated search and retrieval features
4. Implement authentication for multi-user support

Remember to destroy resources when not in use to avoid charges:
```bash
terraform destroy
```