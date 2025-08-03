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