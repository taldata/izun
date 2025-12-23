# Terraform Configuration for Izun Committee Management System
# AWS Infrastructure: RDS PostgreSQL + Elastic Beanstalk

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Optional: Configure remote backend for state management
  # backend "s3" {
  #   bucket = "izun-terraform-state"
  #   key    = "prod/terraform.tfstate"
  #   region = "il-central-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "izun"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "random" {}
