# VPC and Networking for Izun

# Create VPC if requested
resource "aws_vpc" "main" {
  count = var.create_new_vpc ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.app_name}-vpc"
  }
}

# Use existing or new VPC
locals {
  vpc_id = var.create_new_vpc ? aws_vpc.main[0].id : var.existing_vpc_id
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  count = var.create_new_vpc ? 1 : 0

  vpc_id = local.vpc_id

  tags = {
    Name = "${var.app_name}-igw"
  }
}

# Get available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Public Subnets
resource "aws_subnet" "public" {
  count = var.create_new_vpc ? 2 : 0

  vpc_id                  = local.vpc_id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.app_name}-public-${count.index + 1}"
    Type = "public"
  }
}

# Private Subnets for RDS
resource "aws_subnet" "private" {
  count = var.create_new_vpc ? 2 : 0

  vpc_id            = local.vpc_id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.app_name}-private-${count.index + 1}"
    Type = "private"
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  count = var.create_new_vpc ? 1 : 0

  vpc_id = local.vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = {
    Name = "${var.app_name}-public-rt"
  }
}

# Route Table Association for Public Subnets
resource "aws_route_table_association" "public" {
  count = var.create_new_vpc ? 2 : 0

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# Get subnet IDs for use in other resources
locals {
  public_subnet_ids  = var.create_new_vpc ? aws_subnet.public[*].id : []
  private_subnet_ids = var.create_new_vpc ? aws_subnet.private[*].id : []
}
