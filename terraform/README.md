# Terraform Deployment for Izun

This directory contains Terraform configuration to provision the complete AWS infrastructure for the Izun Committee Management System.

## Prerequisites

1. **Terraform** installed (v1.0.0+)
   ```bash
   brew install terraform
   ```

2. **AWS CLI** configured with credentials
   ```bash
   aws configure
   ```

3. **Azure AD credentials** for authentication

## Infrastructure Components

| Component | Resource | Description |
|-----------|----------|-------------|
| VPC | `aws_vpc` | Virtual Private Cloud with public/private subnets |
| RDS | `aws_db_instance` | PostgreSQL 15 database |
| EB | `aws_elastic_beanstalk_*` | Elastic Beanstalk application and environment |
| Security | `aws_security_group` | Firewall rules for RDS and EB |
| Secrets | `aws_secretsmanager_secret` | Secure storage for DB password |

## Quick Start

### 1. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your Azure AD credentials:
```hcl
azure_tenant_id     = "your-actual-tenant-id"
azure_client_id     = "your-actual-client-id"
azure_client_secret = "your-actual-client-secret"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Plan

```bash
terraform plan
```

### 4. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted.

### 5. Get Outputs

```bash
# View all outputs
terraform output

# Get specific values
terraform output eb_endpoint_url
terraform output azure_redirect_uri
terraform output -raw database_url_full  # Includes password
```

## Post-Deployment Steps

### 1. Deploy Application Code

```bash
cd ..  # Back to project root
eb deploy izun-production
```

### 2. Migrate Data (if from Render)

```bash
# Export from Render
python upload_db.py

# Import to RDS
export DATABASE_URL=$(cd terraform && terraform output -raw database_url_full)
python migrate_to_postgres.py db_export.json
```

### 3. Update Azure AD

Add the redirect URI to your Azure App Registration:
```bash
terraform output azure_redirect_uri
```

### 4. Open Application

```bash
eb open
```

## Estimated Costs

| Resource | Monthly Cost |
|----------|-------------|
| RDS db.t3.micro | ~$15 |
| EB t3.micro | ~$8-10 |
| Storage (20GB) | ~$2 |
| Secrets Manager | ~$0.40 |
| VPC/Networking | Free |
| **Total** | ~$25-30 |

## Destroying Infrastructure

To tear down all resources:

```bash
terraform destroy
```

> ⚠️ **Warning**: This will delete all resources including the RDS database. Make sure to backup your data first!

## Troubleshooting

### State Lock Issues
```bash
terraform force-unlock LOCK_ID
```

### RDS Connection Issues
Check security group allows connections:
```bash
aws ec2 describe-security-groups --group-ids $(terraform output -raw rds_security_group_id)
```

### EB Deployment Failures
```bash
eb logs
eb health
```

## File Structure

```
terraform/
├── main.tf                 # Provider configuration
├── variables.tf            # Input variables
├── vpc.tf                  # VPC and networking
├── security_groups.tf      # Security groups
├── rds.tf                  # RDS PostgreSQL
├── elasticbeanstalk.tf     # Elastic Beanstalk
├── outputs.tf              # Output values
├── terraform.tfvars.example # Example variables
└── README.md               # This file
```
