variable "backend_runtime_secret_name" {
  type = string
}

data "aws_secretsmanager_secret" "backend_runtime" {
  name = var.backend_runtime_secret_name
}

output "backend_runtime_secret_arn" {
  value = data.aws_secretsmanager_secret.backend_runtime.arn
}
