# Elastic Beanstalk Application and Environment for Izun

# Generate Flask secret key
resource "random_password" "flask_secret" {
  length  = 64
  special = false
}

# IAM Role for Elastic Beanstalk EC2 instances
resource "aws_iam_role" "eb_ec2_role" {
  name = "${var.app_name}-eb-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.app_name}-eb-ec2-role"
  }
}

# Attach required policies to EC2 role
resource "aws_iam_role_policy_attachment" "eb_web_tier" {
  role       = aws_iam_role.eb_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier"
}

resource "aws_iam_role_policy_attachment" "eb_worker_tier" {
  role       = aws_iam_role.eb_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier"
}

resource "aws_iam_role_policy_attachment" "eb_multicontainer_docker" {
  role       = aws_iam_role.eb_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker"
}

# Instance Profile
resource "aws_iam_instance_profile" "eb_ec2_profile" {
  name = "${var.app_name}-eb-ec2-profile"
  role = aws_iam_role.eb_ec2_role.name
}

# IAM Service Role for Elastic Beanstalk
resource "aws_iam_role" "eb_service_role" {
  name = "${var.app_name}-eb-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticbeanstalk.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.app_name}-eb-service-role"
  }
}

resource "aws_iam_role_policy_attachment" "eb_enhanced_health" {
  role       = aws_iam_role.eb_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth"
}

resource "aws_iam_role_policy_attachment" "eb_managed_updates" {
  role       = aws_iam_role.eb_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy"
}

# Use existing Elastic Beanstalk Application (already created via eb init)
data "aws_elastic_beanstalk_application" "app" {
  name = var.app_name
}

# Elastic Beanstalk Environment
resource "aws_elastic_beanstalk_environment" "production" {
  name                = "${var.app_name}-${var.environment}"
  application         = data.aws_elastic_beanstalk_application.app.name
  solution_stack_name = var.eb_solution_stack

  # VPC Configuration
  setting {
    namespace = "aws:ec2:vpc"
    name      = "VPCId"
    value     = local.vpc_id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = join(",", var.create_new_vpc ? local.public_subnet_ids : [])
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "AssociatePublicIpAddress"
    value     = "true"
  }

  # Instance Configuration
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = var.eb_instance_type
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile.eb_ec2_profile.name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = aws_security_group.eb.id
  }

  # Environment Type (single instance for cost savings)
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = aws_iam_role.eb_service_role.arn
  }

  # Python Configuration
  setting {
    namespace = "aws:elasticbeanstalk:container:python"
    name      = "WSGIPath"
    value     = "application:application"
  }

  # Environment Variables
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_URL"
    value     = "postgresql://${var.db_username}:${local.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "FLASK_ENV"
    value     = "production"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "SECRET_KEY"
    value     = random_password.flask_secret.result
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AZURE_TENANT_ID"
    value     = var.azure_tenant_id
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AZURE_CLIENT_ID"
    value     = var.azure_client_id
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AZURE_CLIENT_SECRET"
    value     = var.azure_client_secret
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AZURE_REDIRECT_URI"
    value     = "https://${var.app_name}-${var.environment}.${var.aws_region}.elasticbeanstalk.com/auth/callback"
  }

  # Health Reporting
  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  }

  # CloudWatch Logs
  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "DeleteOnTerminate"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "RetentionInDays"
    value     = "7"
  }

  depends_on = [aws_db_instance.postgres]

  tags = {
    Name = "${var.app_name}-${var.environment}"
  }
}
