#!/usr/bin/env python3
"""
Deploy all Part 6 Lambda functions to AWS.
This script packages and deploys all agent Lambda functions via S3.

Usage:
    cd backend
    uv run deploy_all_lambdas.py [--package]
    
Options:
    --package    Force re-packaging of all Lambda functions before deployment
"""

import boto3
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

def deploy_lambda_function(function_name: str, zip_path: Path, bucket_name: str) -> bool:
    """
    Deploy a single Lambda function via S3.
    
    Args:
        function_name: Name of the Lambda function
        zip_path: Path to the deployment package
        bucket_name: S3 bucket for Lambda packages
        
    Returns:
        True if successful, False otherwise
    """
    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')
    
    # Check if zip file exists
    if not zip_path.exists():
        print(f"❌ {zip_path} not found. Run package_docker.py first.")
        return False
    
    # Upload to S3
    s3_key = f"lambda-packages/{function_name}.zip"
    print(f"📦 Uploading {function_name} to S3...")
    
    try:
        with open(zip_path, 'rb') as f:
            s3_client.upload_fileobj(f, bucket_name, s3_key)
        print(f"   ✓ Uploaded to s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"   ✗ Failed to upload: {e}")
        return False
    
    # Update Lambda function code
    print(f"🚀 Updating Lambda function {function_name}...")
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            S3Bucket=bucket_name,
            S3Key=s3_key
        )
        
        # Wait for update to complete
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=function_name)
        
        print(f"   ✓ Successfully updated {function_name}")
        return True
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ⚠️  Function {function_name} not found in AWS")
        print(f"      Run terraform apply first to create the Lambda function")
        return False
    except Exception as e:
        print(f"   ✗ Failed to update: {e}")
        return False

def package_lambda(service_name: str, service_dir: Path) -> bool:
    """
    Package a Lambda function using package_docker.py.
    
    Args:
        service_name: Name of the service (e.g., 'planner')
        service_dir: Path to the service directory
        
    Returns:
        True if successful, False otherwise
    """
    print(f"   📦 Packaging {service_name}...")
    
    package_script = service_dir / 'package_docker.py'
    if not package_script.exists():
        print(f"      ✗ package_docker.py not found in {service_dir}")
        return False
    
    try:
        # Run uv run package_docker.py in the service directory
        result = subprocess.run(
            ['uv', 'run', 'package_docker.py'],
            cwd=service_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Check if zip was created
            zip_path = service_dir / f'{service_name}_lambda.zip'
            if zip_path.exists():
                size_mb = zip_path.stat().st_size / (1024 * 1024)
                print(f"      ✓ Created {size_mb:.1f} MB package")
                return True
            else:
                print(f"      ✗ Package not created")
                return False
        else:
            print(f"      ✗ Packaging failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"      ✗ Error running package_docker.py: {e}")
        return False

def main():
    """Main deployment function."""
    # Check for --package flag
    force_package = '--package' in sys.argv
    
    print("🎯 Deploying Alex Agent Lambda Functions")
    print("=" * 50)
    
    # Get AWS account ID
    try:
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.Session().region_name
        print(f"AWS Account: {account_id}")
        print(f"AWS Region: {region}")
    except Exception as e:
        print(f"❌ Failed to get AWS account info: {e}")
        print("   Make sure your AWS credentials are configured")
        sys.exit(1)
    
    # S3 bucket name
    bucket_name = f"alex-lambda-packages-{account_id}"
    
    # Ensure S3 bucket exists
    s3_client = boto3.client('s3')
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"S3 Bucket: {bucket_name} ✓")
    except:
        print(f"❌ S3 bucket {bucket_name} not found")
        print("   Run terraform apply to create the infrastructure")
        sys.exit(1)
    
    print()
    
    # Define Lambda functions to deploy
    backend_dir = Path(__file__).parent
    functions: List[Tuple[str, str, Path]] = [
        ('alex-planner', 'planner', backend_dir / 'planner' / 'planner_lambda.zip'),
        ('alex-tagger', 'tagger', backend_dir / 'tagger' / 'tagger_lambda.zip'),
        ('alex-reporter', 'reporter', backend_dir / 'reporter' / 'reporter_lambda.zip'),
        ('alex-charter', 'charter', backend_dir / 'charter' / 'charter_lambda.zip'),
        ('alex-retirement', 'retirement', backend_dir / 'retirement' / 'retirement_lambda.zip'),
    ]
    
    # Check if packages exist and optionally package them
    print("📋 Checking deployment packages...")
    missing_packages = []
    services_to_package = []
    
    for func_name, service_name, zip_path in functions:
        service_dir = backend_dir / service_name
        
        if force_package:
            # Force re-packaging all services
            services_to_package.append((service_name, service_dir))
            print(f"   ⟳ {service_name}: Will re-package")
        elif zip_path.exists():
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ {service_name}: {size_mb:.1f} MB")
        else:
            print(f"   ✗ {service_name}: Not found")
            missing_packages.append((service_name, service_dir))
            services_to_package.append((service_name, service_dir))
    
    # Package missing or all services if requested
    if services_to_package:
        print()
        print("📦 Packaging Lambda functions...")
        failed_packages = []
        
        for service_name, service_dir in services_to_package:
            if not package_lambda(service_name, service_dir):
                failed_packages.append(service_name)
        
        if failed_packages:
            print()
            print(f"❌ Failed to package: {', '.join(failed_packages)}")
            print("   Make sure Docker is running and package_docker.py exists")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    print()
    print("🚀 Deploying Lambda functions...")
    print("-" * 50)
    
    # Deploy each function
    success_count = 0
    failed_functions = []
    
    for func_name, service_name, zip_path in functions:
        if deploy_lambda_function(func_name, zip_path, bucket_name):
            success_count += 1
        else:
            failed_functions.append(func_name)
        print()
    
    # Summary
    print("=" * 50)
    print(f"✅ Deployment Summary:")
    print(f"   • Successful: {success_count}/{len(functions)}")
    
    if failed_functions:
        print(f"   • Failed: {', '.join(failed_functions)}")
        print()
        print("💡 Troubleshooting tips:")
        print("   1. Check if Lambda functions exist: aws lambda list-functions")
        print("   2. Run terraform apply to create missing functions")
        print("   3. Ensure deployment packages exist (run package_docker.py)")
        print("   4. Check AWS credentials and permissions")
    else:
        print()
        print("🎉 All Lambda functions deployed successfully!")
        print()
        print("Next steps:")
        print("   1. Test individual functions: cd <service> && uv run test_local.py")
        print("   2. Run integration test: cd planner && uv run test_integration.py")
        print("   3. Submit a job via SQS to test the full orchestration")

if __name__ == "__main__":
    main()