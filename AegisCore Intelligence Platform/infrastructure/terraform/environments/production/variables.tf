# Variables for AegisCore Production Environment

variable "aws_region" {
  description = "AWS region for production deployment"
  type        = string
  default     = "us-east-1"
}

variable "allowed_cidr_blocks" {
  description = "Allowed CIDR blocks for administrative access"
  type        = list(string)
  default     = []
}

variable "vpn_cidr" {
  description = "CIDR block for VPN access"
  type        = string
  default     = "10.1.0.0/16"
}
