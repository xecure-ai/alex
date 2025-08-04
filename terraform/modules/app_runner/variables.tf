variable "service_name" {
  description = "Name of the App Runner service"
  type        = string
  default     = "alex-researcher"
}

variable "cpu" {
  description = "CPU units for the service (0.25, 0.5, 1, 2, 4)"
  type        = string
  default     = "0.5"
}

variable "memory" {
  description = "Memory for the service (0.5, 1, 2, 3, 4, 6, 8, 10, 12)"
  type        = string
  default     = "1"
}

variable "environment_variables" {
  description = "Environment variables for the service"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}