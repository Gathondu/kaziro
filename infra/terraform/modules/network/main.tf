data "aws_availability_zones" "available" {
  state = "available"
}

variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project}-${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, 0)
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project}-${var.environment}-public-a"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, 1)
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project}-${var.environment}-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, 2)
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project}-${var.environment}-private-b"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
}

resource "aws_route" "private_outbound" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "apprunner" {
  name   = "${var.project}-${var.environment}-apprunner"
  vpc_id = aws_vpc.this.id
}

resource "aws_vpc_security_group_egress_rule" "apprunner_all" {
  security_group_id = aws_security_group.apprunner.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "ecs" {
  name   = "${var.project}-${var.environment}-ecs"
  vpc_id = aws_vpc.this.id
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "valkey" {
  name   = "${var.project}-${var.environment}-valkey"
  vpc_id = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "valkey_from_apprunner" {
  security_group_id            = aws_security_group.valkey.id
  referenced_security_group_id = aws_security_group.apprunner.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "valkey_from_ecs" {
  security_group_id            = aws_security_group.valkey.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "private_subnet_ids" {
  value = [aws_subnet.private.id, aws_subnet.private_b.id]
}

output "public_subnet_ids" {
  value = [aws_subnet.public.id]
}

output "apprunner_security_group_id" {
  value = aws_security_group.apprunner.id
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}

output "valkey_security_group_id" {
  value = aws_security_group.valkey.id
}
