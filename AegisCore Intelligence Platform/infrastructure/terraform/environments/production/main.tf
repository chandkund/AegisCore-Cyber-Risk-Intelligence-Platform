# AegisCore Production Infrastructure
# Includes WAF, RDS with encryption, and compliance configurations

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "aegiscore-terraform-state-production"
    key            = "infrastructure/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "aegiscore-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "aegiscore"
      ManagedBy   = "terraform"
      CostCenter  = "security-infrastructure"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================
# AWS WAF Configuration
# ============================================================

module "waf" {
  source = "../../modules/waf"

  project_name = "aegiscore"
  environment  = "production"
  scope        = "REGIONAL" # For ALB association

  # Rate limiting - stricter for production
  rate_limit_general = 1000  # 1000 requests per 5 minutes
  rate_limit_auth    = 50    # 50 auth requests per 5 minutes

  # Geographic restrictions - enable for compliance
  geo_restriction_enabled = true
  blocked_countries = [
    "CN", # China
    "RU", # Russia
    "KP", # North Korea
    "IR", # Iran
    "BY", # Belarus
    "CU", # Cuba
    "SY", # Syria
    "VE", # Venezuela
  ]

  # Internal IPs (excluded from rate limiting)
  # Add your VPN and office IP ranges here
  internal_ip_patterns = [
    "10\\.0\\.\\d+\\.\\d+",      # VPC CIDR
    "10\\.1\\.\\d+\\.\\d+",      # VPN CIDR
  ]

  enable_logging = true

  tags = {
    Compliance = "SOC2"
    Criticality = "High"
  }
}

# ============================================================
# RDS PostgreSQL with Encryption
# ============================================================

resource "aws_db_instance" "primary" {
  identifier = "aegiscore-production-primary"

  engine         = "postgres"
  engine_version = "15.5"

  instance_class    = "db.r6g.xlarge"
  allocated_storage = 100
  storage_type      = "gp3"
  storage_encrypted = true # TDE - Encryption at rest
  kms_key_id        = aws_kms_key.rds.arn

  db_name  = "aegiscore"
  username = "aegiscore_admin"
  password = random_password.rds_master.result

  multi_az               = true
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  # Enhanced monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Performance insights
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn

  # Deletion protection
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "aegiscore-production-final"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name        = "aegiscore-production-primary"
    Compliance  = "SOC2"
    Criticality = "Critical"
  }
}

# KMS Key for RDS Encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption at rest"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow RDS Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "aegiscore-rds-encryption-key"
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/aegiscore-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# Random password for RDS master user
resource "random_password" "rds_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store RDS password in Secrets Manager
resource "aws_secretsmanager_secret" "rds_master" {
  name                    = "aegiscore/production/rds-master-password"
  description             = "Master password for AegisCore production RDS"
  recovery_window_in_days = 30
  kms_key_id              = aws_kms_key.secrets.arn

  tags = {
    Compliance = "SOC2"
  }
}

resource "aws_secretsmanager_secret_version" "rds_master" {
  secret_id     = aws_secretsmanager_secret.rds_master.id
  secret_string = random_password.rds_master.result
}

# KMS Key for Secrets Manager
resource "aws_kms_key" "secrets" {
  description             = "KMS key for Secrets Manager encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "aegiscore-secrets-encryption-key"
  }
}

# ============================================================
# VPC and Networking
# ============================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "aegiscore-production-vpc"
  }
}

resource "aws_db_subnet_group" "rds" {
  name       = "aegiscore-production-rds"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name = "aegiscore-production-rds-subnet-group"
  }
}

resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "aegiscore-production-private-1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "aegiscore-production-private-2"
  }
}

# ============================================================
# Security Groups
# ============================================================

resource "aws_security_group" "rds" {
  name        = "aegiscore-production-rds"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "aegiscore-production-rds-sg"
  }
}

resource "aws_security_group" "application" {
  name        = "aegiscore-production-app"
  description = "Security group for application servers"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "aegiscore-production-app-sg"
  }
}

resource "aws_security_group" "alb" {
  name        = "aegiscore-production-alb"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "aegiscore-production-alb-sg"
  }
}

# ============================================================
# Application Load Balancer with WAF
# ============================================================

resource "aws_lb" "main" {
  name               = "aegiscore-production"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  enable_deletion_protection = true
  enable_http2               = true
  idle_timeout               = 60

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb-logs"
    enabled = true
  }

  tags = {
    Name = "aegiscore-production-alb"
  }
}

resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.101.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "aegiscore-production-public-1"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.102.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = {
    Name = "aegiscore-production-public-2"
  }
}

resource "aws_s3_bucket" "alb_logs" {
  bucket = "aegiscore-production-alb-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "aegiscore-production-alb-logs"
  }
}

# WAF Association with ALB
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = module.waf.web_acl_arn
}

# ============================================================
# IAM Roles
# ============================================================

resource "aws_iam_role" "rds_monitoring" {
  name = "aegiscore-production-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
