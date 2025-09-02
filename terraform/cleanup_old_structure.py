#!/usr/bin/env python3
"""
Script to help clean up the old Terraform structure after migration to separate directories.
This script identifies files that can be safely removed from the old monolithic structure.
"""

import os
from pathlib import Path

def main():
    """Identify old Terraform files that can be cleaned up."""
    
    terraform_root = Path(__file__).parent
    
    # Files from the old monolithic structure
    old_files = [
        "main.tf",
        "variables.tf", 
        "outputs.tf",
        "lambda_part6.tf",
        "lambda.tf.bak",
        ".terraform.lock.hcl",
        "aurora.tfplan",
        "aurora_deploy.log",
        "aurora_deploy_2.log",
        "response.json",
        "terraform.tfstate",
        "terraform.tfstate.backup"
    ]
    
    # Old module directories that are no longer needed
    old_modules = [
        "modules/app_runner",
        "modules/opensearch",
        "modules/api_gateway",
        "modules/scheduler",
        "modules/aurora",
        "modules/lambda_s3vectors",
        "modules/s3_vectors",
        "modules/rds",
        "modules/cloudfront",
        "modules/langfuse"
    ]
    
    print("=" * 60)
    print("Terraform Structure Cleanup Helper")
    print("=" * 60)
    print("\nThe Terraform structure has been reorganized into separate directories.")
    print("Each guide now has its own Terraform directory with local state.\n")
    
    print("Files from the old structure that can be removed:")
    print("-" * 60)
    
    files_found = []
    for file in old_files:
        file_path = terraform_root / file
        if file_path.exists():
            files_found.append(file)
            print(f"  ✓ {file}")
    
    if not files_found:
        print("  No old files found - already cleaned!")
    
    print("\nOld module directories that can be removed:")
    print("-" * 60)
    
    modules_found = []
    for module in old_modules:
        module_path = terraform_root / module
        if module_path.exists():
            modules_found.append(module)
            print(f"  ✓ {module}/")
    
    if not modules_found:
        print("  No old modules found - already cleaned!")
    
    if files_found or modules_found:
        print("\n" + "=" * 60)
        print("IMPORTANT: Before removing these files:")
        print("=" * 60)
        print("1. Ensure you have successfully deployed using the new structure")
        print("2. Back up any terraform.tfstate files if you need to import resources")
        print("3. The new structure is in terraform/2_sagemaker, terraform/3_ingestion, etc.")
        print("\nTo remove these files, you can run:")
        print("-" * 60)
        
        if files_found:
            print("\n# Remove old files:")
            for file in files_found:
                print(f"rm terraform/{file}")
        
        if modules_found:
            print("\n# Remove old modules:")
            for module in modules_found:
                print(f"rm -rf terraform/{module}")
        
        print("\n# Or remove everything at once (BE CAREFUL!):")
        print("# cd terraform")
        if files_found:
            files_str = " ".join(files_found)
            print(f"# rm {files_str}")
        if modules_found:
            print("# rm -rf modules/")
    else:
        print("\n✅ Cleanup complete! The old Terraform structure has been removed.")
        print("\nYour new Terraform structure:")
        print("  terraform/2_sagemaker/   - Part 2 infrastructure")
        print("  terraform/3_ingestion/   - Part 3 infrastructure")
        print("  terraform/4_researcher/  - Part 4 infrastructure")
        print("  terraform/5_database/    - Part 5 infrastructure")
        print("  terraform/6_agents/      - Part 6 infrastructure")
    
    print("\n" + "=" * 60)
    print("Note: Each directory maintains its own local terraform.tfstate")
    print("These state files are gitignored for security.")
    print("=" * 60)

if __name__ == "__main__":
    main()