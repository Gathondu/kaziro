data "aws_iam_policy_document" "assume_apprunner" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "assume_tasks" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "instance_permissions" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      var.backend_runtime_secret_arn
    ]
  }
}

variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "image_uri" {
  type = string
}

variable "backend_runtime_secret_arn" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "cpu" {
  type = string
}

variable "memory" {
  type = string
}

variable "redis_url" {
  type = string
}

resource "aws_iam_role" "access" {
  name               = "${var.project}-${var.environment}-apprunner-access"
  assume_role_policy = data.aws_iam_policy_document.assume_apprunner.json
}

resource "aws_iam_role_policy_attachment" "ecr" {
  role       = aws_iam_role.access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "instance" {
  name               = "${var.project}-${var.environment}-apprunner-instance"
  assume_role_policy = data.aws_iam_policy_document.assume_tasks.json
}

resource "aws_iam_role_policy" "instance" {
  name   = "${var.project}-${var.environment}-apprunner-instance"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.instance_permissions.json
}

resource "aws_apprunner_vpc_connector" "this" {
  vpc_connector_name = "${var.project}-${var.environment}-connector"
  subnets            = var.private_subnet_ids
  security_groups    = var.security_group_ids
}

resource "aws_apprunner_service" "this" {
  service_name = "${var.project}-${var.environment}-api"

  source_configuration {
    auto_deployments_enabled = false
    authentication_configuration {
      access_role_arn = aws_iam_role.access.arn
    }

    image_repository {
      image_repository_type = "ECR"
      image_identifier      = var.image_uri
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          REDIS_URL = var.redis_url
        }
        runtime_environment_secrets = {
          KAZIRO_BACKEND_ENV_JSON = var.backend_runtime_secret_arn
        }
      }
    }
  }

  instance_configuration {
    cpu               = var.cpu
    memory            = var.memory
    instance_role_arn = aws_iam_role.instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.this.arn
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    healthy_threshold   = 1
    unhealthy_threshold = 5
    interval            = 10
    timeout             = 5
  }
}

output "service_url" {
  value = aws_apprunner_service.this.service_url
}
