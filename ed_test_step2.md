# Part 7 Step 2: Deployment Test

## Quick Prerequisites Check
```bash
docker info | head -2  # Docker running?
terraform --version    # Terraform installed?
aws sts get-caller-identity  # AWS configured?
```

## Deploy

### Option 1: Full automated deployment
```bash
cd /Users/ed/projects/alex/scripts
uv run deploy.py
```
Type 'yes' when Terraform prompts.

### Option 2: Manual steps (for debugging)
```bash
# 1. Package Lambda
cd /Users/ed/projects/alex/backend/api
uv run package_docker.py
# Should create api_lambda.zip (~22 MB)

# 2. Build frontend
cd /Users/ed/projects/alex/frontend
npm run build
# Should create out/ directory

# 3. Deploy infrastructure
cd /Users/ed/projects/alex/terraform/7_frontend
terraform apply

# 4. Upload frontend (get bucket name from terraform output)
aws s3 sync /Users/ed/projects/alex/frontend/out/ s3://[bucket-name]/ --delete

# 5. Get CloudFront URL from terraform output
```

## Test Deployment

1. **Visit CloudFront URL** - Should see landing page
2. **Sign in with Clerk** - Should redirect to dashboard
3. **Check database for user**:
```bash
cd /Users/ed/projects/alex/backend/database
uv run python -c "
from src import Database
db = Database()
users = db.users.find_all()
for u in users: print(f'{u.display_name}: {u.clerk_user_id}')
"
```
4. **Check Lambda logs**:
```bash
aws logs tail /aws/lambda/alex-api --follow
```

## Destroy
```bash
cd /Users/ed/projects/alex/scripts
uv run destroy.py
```

## Expected Outputs
- CloudFront URL: `https://[dist-id].cloudfront.net`
- API Gateway: `https://[api-id].execute-api.us-east-1.amazonaws.com`
- Lambda: `alex-api`
- S3 Bucket: `alex-frontend-[account-id]`