#!/usr/bin/env python3
"""
Package the InstrumentTagger for Lambda deployment using Docker.
This ensures binary compatibility with Lambda's Linux x86_64 runtime.
"""

import os
import shutil
import zipfile
import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("InstrumentTagger Lambda Packaging (Docker)")
    print("=" * 60)
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker is not installed or not available")
        print("   Please install Docker to use this packaging script")
        sys.exit(1)
    
    print("\n📦 Creating Lambda deployment package...")

    # Clean up
    package_dir = Path("lambda-package")
    zip_file = Path("tagger_lambda.zip")
    
    if package_dir.exists():
        shutil.rmtree(package_dir)
    if zip_file.exists():
        os.remove(zip_file)

    # Create package directory
    package_dir.mkdir()

    # Create requirements.txt for Docker pip install
    print("\n📝 Creating requirements.txt...")
    requirements = [
        "boto3>=1.40.9",
        "pydantic>=2.11.7", 
        "python-dotenv>=1.1.1",
        "openai-agents[litellm]>=0.2.6"
    ]
    
    with open("requirements_docker.txt", "w") as f:
        f.write("\n".join(requirements))

    # Install dependencies using Docker with Lambda runtime image
    print("\n🐳 Installing dependencies using Lambda runtime container...")
    print("   Using: public.ecr.aws/lambda/python:3.12")
    print("   Platform: linux/amd64 (x86_64)")
    
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.getcwd()}:/var/task",
            "-v",
            f"{os.path.abspath('../database')}:/var/database",
            "--platform",
            "linux/amd64",  # Force x86_64 architecture for Lambda
            "--entrypoint",
            "",  # Override the default entrypoint
            "public.ecr.aws/lambda/python:3.12",
            "/bin/sh",
            "-c",
            # Install requirements and the database package
            "pip install --target /var/task/lambda-package "
            "-r /var/task/requirements_docker.txt "
            "--only-binary=:all: --upgrade && "
            "pip install --target /var/task/lambda-package /var/database"
        ],
        check=True,
    )

    # Copy application files
    print("\n📄 Copying application files...")
    app_files = [
        "lambda_handler.py",
        "agent.py", 
        "templates.py"
    ]
    
    for file in app_files:
        if Path(file).exists():
            shutil.copy2(file, package_dir)
            print(f"   ✓ {file}")
        else:
            print(f"   ⚠ {file} not found")

    # Create zip
    print("\n🗜️  Creating zip file...")
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ and other unnecessary directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pytest_cache', 'tests']]
            
            for file in files:
                # Skip .pyc and other unnecessary files
                if file.endswith(('.pyc', '.pyo', '.pyi')):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)

    # Show package size
    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"\n✅ Created {zip_file} ({size_mb:.2f} MB)")
    
    # Clean up temp files
    os.remove("requirements_docker.txt")
    shutil.rmtree(package_dir)
    
    # Deploy if requested
    if "--deploy" in sys.argv:
        print("\n🚀 Deploying to Lambda...")
        deploy_to_lambda(str(zip_file))
    else:
        print("\n📝 Next steps:")
        print(f"   1. Deploy: uv run package_docker.py --deploy")
        print(f"   2. Test: uv run test_lambda.py")


def deploy_to_lambda(zip_path):
    """Deploy the package to Lambda."""
    import boto3
    
    lambda_client = boto3.client('lambda')
    function_name = 'alex-tagger'
    
    try:
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        print(f"   ✅ Function updated: {function_name}")
        print(f"      Last modified: {response['LastModified']}")
        print(f"      Code size: {response['CodeSize'] / (1024*1024):.2f} MB")
        
        # Wait for update to complete
        print("\n   ⏳ Waiting for function to be ready...")
        import time
        time.sleep(10)
        
        print("\n   ✅ Deployment complete!")
        print("      Test with: uv run test_lambda.py")
        
    except Exception as e:
        print(f"   ❌ Deployment failed: {e}")


if __name__ == "__main__":
    main()