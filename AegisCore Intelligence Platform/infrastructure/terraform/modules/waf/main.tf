# AWS WAF v2 WebACL for AegisCore Production
# Provides OWASP Top 10 protection, rate limiting, and geographic controls

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS WAF WebACL
resource "aws_wafv2_web_acl" "main" {
  name        = "${var.project_name}-${var.environment}-waf"
  description = "WAF rules for ${var.project_name} ${var.environment}"
  scope       = var.scope # REGIONAL for ALB, CLOUDFRONT for CloudFront

  default_action {
    allow {}
  }

  # Rule 1: AWS Managed Rule - Common Rule Set (OWASP Top 10)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Override specific rules if needed
        rule_action_override {
          action_to_use {
            count {}
          }
          name = "SizeRestrictions_BODY" # Allow larger payloads for uploads
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed Rule - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed Rule - SQL Injection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed Rule - Linux OS Protections
  rule {
    name     = "AWSManagedRulesLinuxOSRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxOSRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesLinuxOSRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 5: AWS Managed Rule - PHP Application Protections
  rule {
    name     = "AWSManagedRulesPHPRuleSet"
    priority = 5

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesPHPRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesPHPRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 6: AWS Managed Rule - WordPress Protections
  rule {
    name     = "AWSManagedRulesWordPressRuleSet"
    priority = 6

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesWordPressRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesWordPressRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 7: Rate Limiting - General API
  rule {
    name     = "RateLimitGeneral"
    priority = 7

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit_general
        aggregate_key_type = "IP"

        scope_down_statement {
          not_statement {
            statement {
              regex_pattern_set_reference_statement {
                arn = aws_wafv2_regex_pattern_set.internal_ips.arn
                field_to_match {
                  single_header {
                    name = "x-forwarded-for"
                  }
                }
                text_transformation {
                  priority = 0
                  type     = "LOWERCASE"
                }
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitGeneralMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 8: Rate Limiting - Strict for Auth Endpoints
  rule {
    name     = "RateLimitAuth"
    priority = 8

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit_auth
        aggregate_key_type = "IP"

        scope_down_statement {
          or_statement {
            statement {
              byte_match_statement {
                search_string         = "/api/v1/auth/login"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "LOWERCASE"
                }
                positional_constraint = "CONTAINS"
              }
            }
            statement {
              byte_match_statement {
                search_string         = "/api/v1/auth/register"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "LOWERCASE"
                }
                positional_constraint = "CONTAINS"
              }
            }
            statement {
              byte_match_statement {
                search_string         = "/api/v1/auth/refresh"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "LOWERCASE"
                }
                positional_constraint = "CONTAINS"
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitAuthMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 9: Geographic Restrictions (if enabled)
  dynamic "rule" {
    for_each = var.geo_restriction_enabled ? [1] : []

    content {
      name     = "GeoRestriction"
      priority = 9

      action {
        block {
          custom_response {
            response_code = 403
            custom_response_body_key = "geo-blocked"
          }
        }
      }

      statement {
        geo_match_statement {
          country_codes = var.blocked_countries
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "GeoRestrictionMetric"
        sampled_requests_enabled   = true
      }
    }
  }

  # Rule 10: IP Reputation - AWS Managed
  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 10

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAmazonIpReputationListMetric"
      sampled_requests_enabled   = true
    }
  }

  # Rule 11: Anonymous IP List (VPN, Tor, etc)
  rule {
    name     = "AWSManagedRulesAnonymousIpList"
    priority = 11

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"

        rule_action_override {
          action_to_use {
            count {} # Count only, don't block (may block legitimate VPN users)
          }
          name = "HostingProviderIPList"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesAnonymousIpListMetric"
      sampled_requests_enabled   = true
    }
  }

  # Custom Response Bodies
  custom_response_body {
    key          = "geo-blocked"
    content      = "Access denied: Your location is not authorized to access this resource."
    content_type = "TEXT_PLAIN"
  }

  # Logging Configuration
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-${var.environment}-waf-metric"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

# Regex Pattern Set for Internal IPs (excluded from rate limiting)
resource "aws_wafv2_regex_pattern_set" "internal_ips" {
  name  = "${var.project_name}-${var.environment}-internal-ips"
  scope = var.scope

  # Add your internal/VPN IP ranges here
  # Example: "10\\.0\\.\\d+\\.\\d+" for 10.0.x.x
  
  dynamic "regular_expression" {
    for_each = var.internal_ip_patterns
    content {
      regex_string = regular_expression.value
    }
  }

  tags = var.tags
}

# WAF Logging to S3 (for compliance and analysis)
resource "aws_wafv2_web_acl_logging_configuration" "main" {
  count = var.enable_logging ? 1 : 0

  log_destination_configs = [aws_kinesis_firehose_delivery_stream.waf_logs[0].arn]
  resource_arn            = aws_wafv2_web_acl.main.arn

  logging_filter {
    default_behavior = "KEEP"

    filter {
      behavior = "KEEP"
      condition {
        action_condition {
          action = "BLOCK"
        }
      }
      requirement = "MEETS_ANY"
    }
  }
}

# Kinesis Firehose for WAF logs (optional)
resource "aws_kinesis_firehose_delivery_stream" "waf_logs" {
  count = var.enable_logging ? 1 : 0

  name        = "${var.project_name}-${var.environment}-waf-logs"
  destination = "s3"

  s3_configuration {
    role_arn           = aws_iam_role.firehose[0].arn
    bucket_arn         = aws_s3_bucket.waf_logs[0].arn
    prefix             = "waf-logs/"
    compression_format = "GZIP"
  }
}

# S3 Bucket for WAF logs
resource "aws_s3_bucket" "waf_logs" {
  count  = var.enable_logging ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-waf-logs-${data.aws_caller_identity.current.account_id}"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "waf_logs" {
  count  = var.enable_logging ? 1 : 0
  bucket = aws_s3_bucket.waf_logs[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "waf_logs" {
  count  = var.enable_logging ? 1 : 0
  bucket = aws_s3_bucket.waf_logs[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}

# IAM Role for Firehose
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "firehose" {
  count = var.enable_logging ? 1 : 0
  name  = "${var.project_name}-${var.environment}-firehose-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "firehose.amazonaws.com"
        }
      }
    ]
  })
}

# CloudWatch Alarms for WAF
resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "${var.project_name}-${var.environment}-waf-blocked-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "WAF is blocking more than 100 requests per 5 minutes"

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = data.aws_region.current.name
  }

  tags = var.tags
}

data "aws_region" "current" {}
