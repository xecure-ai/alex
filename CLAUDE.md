# Project: Alex

## Overall context
- This is a project being developed as part of Ed's course "AI in Production"
- Ed is writing this code which thousands of students will clone; they will then follow the steps to deploy
- Students may be on Windows PC, Mac or Linux; the instructions needs to work on all systems
- This project is called Alex - the Agentic Lifetime Equities Explainer - it's an Agentic AI Platform to be your personal financial planner for your portfolios
- The project root is ~/projects/alex
- There is a .env file in the project root; you may not be able to see it for security reasons, but it's there, with OPENAI_API_KEY

## Project organization
backend
- There will be separate projects within this folder for each of the backend deployments
- Each one will have its own uv project
frontend
- A NextJS typescript app will be built eventually
terraform
- Here will be the terraform scripts for the deployment

## OpenSearch + Lambda Architecture Decisions (August 2025)

### Architecture Approach
Based on research and lessons learned from SageMaker deployment:
1. **OpenSearch Serverless** - Fully managed, auto-scaling vector database
2. **Lambda with inline dependencies** - Simple zip deployment, no layers
3. **API Gateway HTTP API** - Simpler and cheaper than REST API
4. **API Key authentication** - Protect endpoints from public access

### Implementation Decisions
1. **Zip Creation**: Python script for cross-platform compatibility (Windows/Mac/Linux)
2. **Authentication**: API Gateway API keys to prevent unauthorized access and protect SageMaker costs
3. **Terraform Structure**: Separate modules for clarity:
   - `modules/opensearch/` - OpenSearch Serverless resources
   - `modules/lambda/` - Lambda function and IAM
   - `modules/api_gateway/` - API Gateway and authentication
   
### Key Principles
- Start simple, mainstream solutions only
- Cross-platform compatibility is mandatory
- Security by default (API keys from start)
- Modular but not complex
- Everything in Terraform for single deployment

## Important Learning: SageMaker Deployment Post-Mortem (August 2025)

### What Happened
We spent 2+ hours implementing a complex custom model packaging approach for deploying all-MiniLM-L6-v2 on SageMaker, involving:
- Custom inference.py scripts
- Model packaging into tar.gz files
- S3 bucket creation and management
- Python/uv project for testing
- Multiple iterations with outdated containers (2023 PyTorch containers in 2025)

### What Went Wrong
1. **Jumped to complexity** - Assumed we needed custom scripts without researching simpler options
2. **Used outdated approaches** - Implemented 2023 patterns when 2025 best practice is much simpler
3. **Ignored context** - Despite being told it's August 2025, searched for 2024 info and used old containers
4. **Didn't validate approach** - Built everything before confirming it was the right way

### The Right Approach (Discovered After 2 Hours)
- Use HuggingFace containers with `HF_MODEL_ID` environment variable
- No model packaging needed - it downloads automatically
- No S3 buckets, no Python code, no custom scripts
- Just Terraform and done

### Going Forward - ALWAYS:
1. **Research current best practices FIRST** - especially check the year
2. **Start with the simplest possible approach** 
3. **Challenge every piece of complexity** - ask "is this necessary?"
4. **Validate the approach before building** - quick proof of concept
5. **Check if this is how everyone else does it** - mainstream solutions for teaching
6. **Pay attention to dates** - if Ed says it's 2025, use 2025 resources

### Key Lesson
For well-supported models like sentence-transformers, the cloud providers have already solved the deployment problem. Look for their simple solution before building a complex one.

## Current Status (Where We Left Off)

### Completed
1. ✅ SageMaker Serverless endpoint deployed (all-MiniLM-L6-v2 model)
2. ✅ Guides 1 and 2 complete and tested
3. ✅ Lambda function code created (`backend/lambda/ingest.py`)
4. ✅ Package.py script created for cross-platform Lambda deployment
5. ✅ Package.py updated to work with uv (removed unnecessary `uv sync` call since `uv run` auto-syncs)

### In Progress
- Setting up Lambda directory with uv project structure
- Need to DELETE `backend/lambda/requirements.txt` (still exists - Bash tool having issues)
- User will run:
  ```bash
  cd backend/lambda
  uv init
  uv python pin 3.12
  uv add opensearch-py requests-aws4auth boto3
  ```

### Next Steps (Not Started)
1. Create Terraform modules:
   - `terraform/modules/opensearch/` - OpenSearch Serverless setup
   - `terraform/modules/lambda/` - Lambda function deployment
   - `terraform/modules/api_gateway/` - API Gateway with API key auth
2. Create guide `3_opensearch_lambda.md`
3. Test complete pipeline end-to-end

### Technical Issues Encountered
- Bash tool having problems with both absolute paths and simple commands
- May need fresh restart to resolve tool issues