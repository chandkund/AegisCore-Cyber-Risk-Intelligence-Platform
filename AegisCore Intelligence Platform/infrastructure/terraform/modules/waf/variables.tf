# Variables for AWS WAF Module

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "aegiscore"
}

variable "environment" {
  description = "Environment (production, staging, development)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "scope" {
  description = "Scope of the WAF WebACL (REGIONAL for ALB, CLOUDFRONT for CloudFront)"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["REGIONAL", "CLOUDFRONT"], var.scope)
    error_message = "Scope must be REGIONAL or CLOUDFRONT."
  }
}

variable "rate_limit_general" {
  description = "General rate limit per 5 minutes per IP"
  type        = number
  default     = 2000
}

variable "rate_limit_auth" {
  description = "Strict rate limit for authentication endpoints per 5 minutes per IP"
  type        = number
  default     = 100
}

variable "geo_restriction_enabled" {
  description = "Enable geographic restrictions"
  type        = bool
  default     = false
}

variable "blocked_countries" {
  description = "List of country codes to block (ISO 3166-1 alpha-2)"
  type        = list(string)
  default     = []
  # Example: ["CN", "RU", "KP", "IR"] for China, Russia, North Korea, Iran
}

variable "internal_ip_patterns" {
  description = "Regex patterns for internal IPs excluded from rate limiting"
  type        = list(string)
  default     = []
  # Example: ["10\\.0\\.\\d+\\.\\d+"] for 10.0.x.x range
}

variable "enable_logging" {
  description = "Enable WAF logging to S3 via Kinesis Firehose"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy = "terraform"
    Project   = "aegiscore"
  }
}
