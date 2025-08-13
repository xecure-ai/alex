#!/usr/bin/env python3
"""
Aurora Cost Management Script
Helps students pause/resume Aurora to save costs during course
"""

import sys
import subprocess
import json
from datetime import datetime

def run_command(cmd):
    """Run AWS CLI command and return result"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def get_cluster_status():
    """Check if Aurora cluster exists and its status"""
    cmd = "aws rds describe-db-clusters --db-cluster-identifier alex-aurora-cluster --region us-east-1 2>/dev/null"
    output = run_command(cmd)
    if not output:
        return None
    
    try:
        data = json.loads(output)
        if data['DBClusters']:
            cluster = data['DBClusters'][0]
            return {
                'exists': True,
                'status': cluster['Status'],
                'endpoint': cluster.get('Endpoint', 'Not available'),
                'scaling': cluster.get('ServerlessV2ScalingConfiguration', {})
            }
    except:
        pass
    return None

def pause_aurora():
    """Scale Aurora down to absolute minimum to save costs"""
    print("🔄 Scaling Aurora to minimum capacity (0.5 ACU)...")
    
    # Scale to minimum
    cmd = """aws rds modify-db-cluster \
        --db-cluster-identifier alex-aurora-cluster \
        --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=0.5 \
        --apply-immediately \
        --region us-east-1"""
    
    result = run_command(cmd)
    if result:
        print("✅ Aurora scaled to minimum (Cost: ~$43/month or ~$1.44/day)")
        print("💡 To completely stop charges, run: python aurora_cost_management.py destroy")
    else:
        print("❌ Failed to scale Aurora")

def resume_aurora():
    """Scale Aurora back to working capacity"""
    print("🔄 Scaling Aurora to working capacity (0.5-1 ACU)...")
    
    cmd = """aws rds modify-db-cluster \
        --db-cluster-identifier alex-aurora-cluster \
        --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=1 \
        --apply-immediately \
        --region us-east-1"""
    
    result = run_command(cmd)
    if result:
        print("✅ Aurora scaled to working capacity (0.5-1 ACU)")
        print("💰 Cost: ~$43-87/month or ~$1.44-2.90/day")
    else:
        print("❌ Failed to scale Aurora")

def destroy_aurora():
    """Completely destroy Aurora to stop all charges"""
    print("⚠️  WARNING: This will DELETE the Aurora cluster and all data!")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm != 'DELETE':
        print("❌ Cancelled")
        return
    
    print("🗑️  Deleting Aurora instance...")
    cmd1 = "aws rds delete-db-instance --db-instance-identifier alex-aurora-cluster-instance-1 --skip-final-snapshot --region us-east-1 2>/dev/null"
    run_command(cmd1)
    
    print("⏳ Waiting for instance deletion...")
    import time
    time.sleep(5)
    
    print("🗑️  Deleting Aurora cluster...")
    cmd2 = "aws rds delete-db-cluster --db-cluster-identifier alex-aurora-cluster --skip-final-snapshot --region us-east-1"
    result = run_command(cmd2)
    
    if result:
        print("✅ Aurora cluster deletion initiated")
        print("💰 Charges will stop once deletion completes (~5-10 minutes)")
    else:
        print("❌ Failed to delete Aurora cluster")

def recreate_aurora():
    """Recreate Aurora cluster using Terraform"""
    print("🔄 Recreating Aurora cluster with Terraform...")
    print("📝 Note: This requires your terraform environment to be set up")
    
    confirm = input("Continue with terraform apply? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    import os
    os.chdir('/Users/ed/projects/alex/terraform')
    
    # Source env vars and run terraform
    cmd = """source ../.env && terraform apply -target=module.aurora \
        -var="aws_account_id=$AWS_ACCOUNT_ID" \
        -var="openai_api_key=$OPENAI_API_KEY" \
        -auto-approve"""
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print("✅ Aurora cluster recreated successfully")
    else:
        print("❌ Failed to recreate Aurora cluster")
        print("💡 Try running terraform manually from the terraform directory")

def show_status():
    """Show current Aurora status and costs"""
    status = get_cluster_status()
    
    if not status or not status['exists']:
        print("❌ Aurora cluster not found")
        print("💡 Run 'python aurora_cost_management.py recreate' to create it")
        return
    
    print("\n📊 Aurora Cluster Status")
    print("=" * 50)
    print(f"Status: {status['status']}")
    print(f"Endpoint: {status['endpoint']}")
    
    if status['scaling']:
        min_cap = status['scaling'].get('MinCapacity', 0)
        max_cap = status['scaling'].get('MaxCapacity', 0)
        print(f"Scaling: {min_cap} - {max_cap} ACUs")
        
        # Calculate costs
        min_cost = min_cap * 0.12 * 24  # Daily cost
        max_cost = max_cap * 0.12 * 24
        
        print(f"\n💰 Estimated Costs:")
        print(f"  Daily: ${min_cost:.2f} - ${max_cost:.2f}")
        print(f"  Monthly: ${min_cost*30:.2f} - ${max_cost*30:.2f}")
        
        if min_cap > 0.5:
            print("\n💡 TIP: Run 'python aurora_cost_management.py pause' to minimize costs")
    
    print("\n📝 Available Commands:")
    print("  pause    - Scale to minimum (0.5 ACU) to reduce costs")
    print("  resume   - Scale to working capacity (0.5-1 ACU)")
    print("  destroy  - DELETE cluster (stops all charges)")
    print("  recreate - Recreate cluster with Terraform")
    print("=" * 50)

def main():
    if len(sys.argv) < 2:
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'pause':
        pause_aurora()
    elif command == 'resume':
        resume_aurora()
    elif command == 'destroy':
        destroy_aurora()
    elif command == 'recreate':
        recreate_aurora()
    elif command == 'status':
        show_status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: uv run aurora_cost_management.py [pause|resume|destroy|recreate|status]")

if __name__ == "__main__":
    main()