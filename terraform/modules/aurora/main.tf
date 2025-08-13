# Aurora Serverless v2 PostgreSQL with Data API

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store database credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  recovery_window_in_days = 0  # Allow immediate deletion for development
  
  # Use random suffix to ensure unique name
  name = "alex-aurora-credentials-${random_password.db_password.id}"
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "alexadmin"
    password = random_password.db_password.result
  })
}

# Data source for default VPC
data "aws_vpc" "default" {
  default = true
}

# Data source for subnets in default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Create DB subnet group using default VPC subnets
resource "aws_db_subnet_group" "alex" {
  name       = "alex-aurora-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
  
  description = "Subnet group for Alex Aurora cluster"
  
  # Tags removed - need ListTagsForResource permission
  
  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

# Aurora Serverless v2 cluster
resource "aws_rds_cluster" "alex_db" {
  cluster_identifier = var.cluster_name
  engine            = "aurora-postgresql"
  engine_mode       = "provisioned"
  engine_version    = "15.4"
  database_name     = var.database_name
  master_username   = "alexadmin"
  master_password   = random_password.db_password.result
  
  # Enable Data API - this is the key feature we need
  enable_http_endpoint = true
  
  # Serverless v2 configuration
  serverlessv2_scaling_configuration {
    max_capacity = var.max_capacity
    min_capacity = var.min_capacity
  }
  
  # Security
  storage_encrypted = true
  
  # Backup
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  
  # Use our subnet group
  db_subnet_group_name = aws_db_subnet_group.alex.name
  
  skip_final_snapshot = true  # For development - change for production
  
  # Tags removed - need ListTagsForResource permission
  
  lifecycle {
    ignore_changes = [tags, tags_all]
  }
  
  depends_on = [aws_db_subnet_group.alex]
}

# Create the actual instance
resource "aws_rds_cluster_instance" "alex_instance" {
  identifier         = "${var.cluster_name}-instance-1"
  cluster_identifier = aws_rds_cluster.alex_db.id
  instance_class     = "db.serverless"
  engine            = aws_rds_cluster.alex_db.engine
  engine_version    = aws_rds_cluster.alex_db.engine_version
  
  # Tags removed - need ListTagsForResource permission
  
  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}