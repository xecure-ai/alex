variable "cluster_name" {
  description = "Name for the Aurora cluster"
  type        = string
  default     = "alex-aurora-cluster"
}

variable "database_name" {
  description = "Name of the default database"
  type        = string
  default     = "alex"
}

variable "min_capacity" {
  description = "Minimum ACU capacity for Serverless v2"
  type        = number
  default     = 0.5  # Minimum possible for cost savings
}

variable "max_capacity" {
  description = "Maximum ACU capacity for Serverless v2"
  type        = number
  default     = 1  # Keep low for development
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "alex"
    Environment = "development"
  }
}