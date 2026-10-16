variable "environment" {
  type        = string
  description = "Target deployment environment"
  default     = "production"
}

variable "region" {
  type        = string
  description = "Cloud provider region"
  default     = "us-east-1"
}

variable "cluster_name" {
  type        = string
  description = "Kubernetes cluster name for RAGOps"
  default     = "ragops-cluster"
}

variable "app_replicas" {
  type        = number
  description = "Initial replica count"
  default     = 3
}
