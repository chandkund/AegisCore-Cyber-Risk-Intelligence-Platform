# Outputs for AWS WAF Module

output "web_acl_arn" {
  description = "ARN of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "web_acl_id" {
  description = "ID of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.id
}

output "web_acl_name" {
  description = "Name of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.name
}

output "web_acl_capacity" {
  description = "Current capacity of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.capacity
}

output "logging_enabled" {
  description = "Whether logging is enabled"
  value       = var.enable_logging
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for WAF logs (if logging enabled)"
  value       = var.enable_logging ? aws_s3_bucket.waf_logs[0].bucket : null
}
