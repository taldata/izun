# RDS PostgreSQL for Izun

# Generate password if not provided
resource "random_password" "db_password" {
  count = var.db_password == "" ? 1 : 0

  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

locals {
  db_password = var.db_password != "" ? var.db_password : random_password.db_password[0].result
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet-group"
  subnet_ids = var.create_new_vpc ? local.private_subnet_ids : local.public_subnet_ids

  tags = {
    Name = "${var.app_name}-db-subnet-group"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "postgres" {
  identifier = "${var.app_name}-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = var.db_engine_version
  instance_class       = var.db_instance_class
  parameter_group_name = aws_db_parameter_group.postgres.name

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 2
  storage_type          = "gp2"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = local.db_password

  # Networking
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.db_publicly_accessible
  port                   = 5432

  # Backup
  backup_retention_period = var.db_backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Other settings
  multi_az                     = false
  auto_minor_version_upgrade   = true
  deletion_protection          = false # Set to true for production
  skip_final_snapshot          = true  # Set to false for production
  final_snapshot_identifier    = "${var.app_name}-final-snapshot"
  copy_tags_to_snapshot        = true
  performance_insights_enabled = false # Enable for production

  tags = {
    Name = "${var.app_name}-postgres"
  }
}

# DB Parameter Group
resource "aws_db_parameter_group" "postgres" {
  family = "postgres15"
  name   = "${var.app_name}-postgres-params"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "${var.app_name}-postgres-params"
  }
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.app_name}/db-password"
  description             = "RDS PostgreSQL password for ${var.app_name}"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.app_name}-db-password"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = local.db_password
    engine   = "postgres"
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = var.db_name
  })
}
