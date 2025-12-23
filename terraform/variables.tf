# Variables for Izun AWS Infrastructure

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "il-central-1"
}

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "izun"
}

# RDS Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "izun"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "izun_admin"
}

variable "db_password" {
  description = "Database master password (leave empty to auto-generate)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.10"
}

variable "db_backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "db_publicly_accessible" {
  description = "Whether the RDS instance is publicly accessible"
  type        = bool
  default     = true
}

# Elastic Beanstalk Configuration
variable "eb_solution_stack" {
  description = "Elastic Beanstalk solution stack name"
  type        = string
  default     = "64bit Amazon Linux 2023 v4.9.0 running Python 3.12"
}

variable "eb_instance_type" {
  description = "EC2 instance type for Elastic Beanstalk"
  type        = string
  default     = "t3.micro"
}

# Azure AD Configuration (for environment variables)
variable "azure_tenant_id" {
  description = "Azure AD Tenant ID"
  type        = string
  sensitive   = true
}

variable "azure_client_id" {
  description = "Azure AD Client ID"
  type        = string
  sensitive   = true
}

variable "azure_client_secret" {
  description = "Azure AD Client Secret"
  type        = string
  sensitive   = true
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "create_new_vpc" {
  description = "Whether to create a new VPC or use existing"
  type        = bool
  default     = true
}

variable "existing_vpc_id" {
  description = "Existing VPC ID (if not creating new)"
  type        = string
  default     = ""
}
