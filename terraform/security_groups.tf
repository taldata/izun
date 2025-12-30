# Security Groups for Izun

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = local.vpc_id

  # Allow PostgreSQL from EB instances
  ingress {
    description     = "PostgreSQL from EB"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eb.id]
  }

  # Allow PostgreSQL from anywhere (for initial setup - can be restricted later)
  # Allow PostgreSQL from anywhere (TEMPORARY: for admin update - REVERTED)
  # ingress {
  #   description = "PostgreSQL from anywhere"
  #   from_port   = 5432
  #   to_port     = 5432
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  # }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-rds-sg"
  }
}

# Security Group for Elastic Beanstalk
resource "aws_security_group" "eb" {
  name        = "${var.app_name}-eb-sg"
  description = "Security group for Elastic Beanstalk instances"
  vpc_id      = local.vpc_id

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH (optional, for debugging)
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
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
    Name = "${var.app_name}-eb-sg"
  }
}
