# Outputs for Izun Terraform Configuration

# RDS Outputs
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = var.db_name
}

output "rds_username" {
  description = "RDS master username"
  value       = var.db_username
}

output "database_url" {
  description = "Full DATABASE_URL for the application"
  value       = "postgresql://${var.db_username}:****@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  sensitive   = false
}

output "database_url_full" {
  description = "Full DATABASE_URL with password (sensitive)"
  value       = "postgresql://${var.db_username}:${local.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  sensitive   = true
}

# Elastic Beanstalk Outputs
output "eb_application_name" {
  description = "Elastic Beanstalk application name"
  value       = data.aws_elastic_beanstalk_application.app.name
}

output "eb_environment_name" {
  description = "Elastic Beanstalk environment name"
  value       = aws_elastic_beanstalk_environment.production.name
}

output "eb_environment_url" {
  description = "Elastic Beanstalk environment URL"
  value       = aws_elastic_beanstalk_environment.production.cname
}

output "eb_endpoint_url" {
  description = "Full application URL"
  value       = "https://${aws_elastic_beanstalk_environment.production.cname}"
}

output "azure_redirect_uri" {
  description = "Azure AD redirect URI to configure"
  value       = "https://${aws_elastic_beanstalk_environment.production.cname}/auth/callback"
}

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = local.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = local.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = local.private_subnet_ids
}

# Security Group Outputs
output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "eb_security_group_id" {
  description = "Elastic Beanstalk security group ID"
  value       = aws_security_group.eb.id
}

# Secrets Manager
output "db_password_secret_arn" {
  description = "ARN of the Secrets Manager secret containing DB password"
  value       = aws_secretsmanager_secret.db_password.arn
}

# CloudFront (managed externally)
# Using existing CloudFront: d2skbotj2u5z8s.cloudfront.net (not managed by Terraform)

output "production_url" {
  description = "Production URL with HTTPS (CloudFront)"
  value       = "https://d2skbotj2u5z8s.cloudfront.net"
}

output "next_steps" {
  description = "Next steps after deployment"
  value       = <<-EOT
    
    Infrastructure deployed successfully!
    
    Production URL: https://d2skbotj2u5z8s.cloudfront.net
    EB URL: http://${aws_elastic_beanstalk_environment.production.cname}
    
    To deploy: eb deploy ${aws_elastic_beanstalk_environment.production.name}
    
  EOT
}
