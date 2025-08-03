# Building Alex: Part 1 - AWS Permissions Setup

Welcome to Project Alex - the Agentic Lifetime Equities Explainer! 

Alex is an AI-powered personal financial planner that will help users manage their investment portfolios and plan for retirement. Throughout this course, we'll build a complete AI system using AWS services.

## What is Alex?

Alex will help users:
- Understand their investment portfolios
- Plan for retirement
- Get personalized financial advice
- Track market trends and opportunities

## About This Guide

This first guide focuses on setting up the necessary AWS permissions. We'll create a dedicated IAM group with only the permissions needed for the Alex project.

## Prerequisites

Before starting, ensure you have:
- An AWS account with root access
- AWS CLI installed and configured with your `aiengineer` IAM user
- Python 3.11 or later
- Basic familiarity with AWS services

## Step 1: Setting Up IAM Permissions

First, we need to create proper IAM permissions for the Alex project. We'll create a dedicated IAM group with only the permissions needed for this project.

### 1.1 Sign in as Root User

1. Navigate to [https://aws.amazon.com/console/](https://aws.amazon.com/console/)
2. Click "Sign In to the Console"
3. Select "Root user" and enter your root email address
4. Click "Next" and enter your root password

⚠️ **Security Note**: We're using the root user only for IAM setup. For all other tasks, we'll use our IAM user.

### 1.2 Create the AlexAccess Group

1. In the AWS Console, navigate to **IAM** (Identity and Access Management)
2. In the left sidebar, click **User groups**
3. Click the **Create group** button
4. For **Group name**, enter: `AlexAccess`
5. In the **Attach permissions policies** section, search for and select these policies:
   - `AmazonSageMakerFullAccess`
   - `AmazonOpenSearchServiceFullAccess`
   
   Note: We already have Lambda, S3, CloudWatch, and API Gateway permissions from other groups.

6. Click **Create group**

### 1.3 Add the Group to Your IAM User

1. Still in IAM, click **Users** in the left sidebar
2. Click on your user `aiengineer`
3. Click the **Groups** tab
4. Click **Add user to groups**
5. Select the checkbox next to `AlexAccess`
6. Click **Add to groups**

### 1.4 Sign Out and Sign Back In

1. Click your username in the top right corner
2. Click **Sign out**
3. Sign back in using your IAM user credentials:
   - Account ID or alias
   - IAM user name: `aiengineer`
   - Your IAM password

### 1.5 Verify Permissions

Let's verify you have the necessary permissions by running:

```bash
aws sts get-caller-identity
```

You should see your IAM user ARN. Next, let's check you can access SageMaker:

```bash
aws sagemaker list-endpoints --region us-east-1
```

This should return an empty list (no error).

## Next Steps

Excellent! You now have the necessary permissions to build Alex. 

Continue to the next guide: [2_sagemaker.md](2_sagemaker.md) where we'll deploy our first AI component - a SageMaker Serverless endpoint for generating text embeddings.

This will be the foundation of Alex's ability to understand and process financial information! 🚀