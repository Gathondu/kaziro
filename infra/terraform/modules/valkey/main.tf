variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "node_type" {
  type = string
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.project}-${var.environment}-valkey-subnets"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = "${var.project}-${var.environment}-valkey"
  description                = "Kaziro Valkey for ${var.environment}"
  engine                     = "valkey"
  engine_version             = "7.2"
  node_type                  = var.node_type
  num_cache_clusters         = 1
  port                       = 6379
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [var.security_group_id]
  automatic_failover_enabled = false
}

output "primary_endpoint_address" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.this.port
}

output "replication_group_id" {
  value = aws_elasticache_replication_group.this.replication_group_id
}
