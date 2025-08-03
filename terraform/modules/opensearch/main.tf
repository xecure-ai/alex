# OpenSearch Serverless Collection for Alex
resource "aws_opensearchserverless_collection" "alex" {
  name = var.collection_name
  type = "VECTORSEARCH"
  
  description = "Vector search collection for Alex - Agentic Lifetime Equities Explainer"
  
  tags = var.tags
  
  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]
}

# Security Policy for the collection
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "${var.collection_name}-encryption"
  type        = "encryption"
  description = "Encryption policy for ${var.collection_name}"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = ["collection/${var.collection_name}"]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network policy to allow access
resource "aws_opensearchserverless_security_policy" "network" {
  name        = "${var.collection_name}-network"
  type        = "network"
  description = "Network policy for ${var.collection_name}"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = ["collection/${var.collection_name}"]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data source for current caller identity
data "aws_caller_identity" "current" {}

# Data access policy for Lambda function and current user
resource "aws_opensearchserverless_access_policy" "data" {
  name        = "${var.collection_name}-data"
  type        = "data"
  description = "Data access policy for ${var.collection_name}"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = ["collection/${var.collection_name}"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = ["index/${var.collection_name}/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument",
            "aoss:DeleteIndex"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        var.lambda_role_arn,
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/aiengineer"  # Allow local development
      ]
    }
  ])
}