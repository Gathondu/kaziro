data "aws_iam_policy_document" "assume_tasks" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "task_permissions" {
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

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "backend_runtime_secret_arn" {
  type = string
}

variable "worker_desired_count" {
  type = number
}

variable "redis_url" {
  type = string
}

resource "aws_ecs_cluster" "this" {
  name = "${var.project}-${var.environment}-cluster"
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project}/${var.environment}/worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${var.project}/${var.environment}/beat"
  retention_in_days = 14
}

resource "aws_iam_role" "execution" {
  name               = "${var.project}-${var.environment}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.assume_tasks.json
}

resource "aws_iam_role_policy_attachment" "execution_default" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${var.project}-${var.environment}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.assume_tasks.json
}

resource "aws_iam_role_policy" "task" {
  name   = "${var.project}-${var.environment}-ecs-task"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_permissions.json
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project}-${var.environment}-worker"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name  = "worker"
      image = var.image_uri
      environment = [
        {
          name  = "REDIS_URL"
          value = var.redis_url
        }
      ]
      command = [
        "uv",
        "run",
        "celery",
        "-A",
        "backend.tasks.celery_app:celery_app",
        "worker",
        "--loglevel=INFO",
        "-Q",
        "default,parser,evaluator,research,document,maintenance"
      ]
      secrets = [
        {
          name      = "KAZIRO_BACKEND_ENV_JSON"
          valueFrom = var.backend_runtime_secret_arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${var.project}-${var.environment}-beat"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name  = "beat"
      image = var.image_uri
      environment = [
        {
          name  = "REDIS_URL"
          value = var.redis_url
        }
      ]
      command = [
        "uv",
        "run",
        "celery",
        "-A",
        "backend.tasks.celery_app:celery_app",
        "beat",
        "--loglevel=INFO"
      ]
      secrets = [
        {
          name      = "KAZIRO_BACKEND_ENV_JSON"
          valueFrom = var.backend_runtime_secret_arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.beat.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "worker" {
  name            = "${var.project}-${var.environment}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [var.security_group_id]
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }
}

resource "aws_ecs_service" "beat" {
  name            = "${var.project}-${var.environment}-beat"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [var.security_group_id]
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }
}

data "aws_region" "current" {}
