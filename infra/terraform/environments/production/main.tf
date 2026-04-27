terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.47"
    }
  }

  backend "s3" {
    bucket       = "kaziro-terraform-state"
    key          = "kaziro/production/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  environment                 = "production"
  backend_image               = "${module.ecr.backend_repository_url}:${var.image_tag}"
  backend_runtime_secret_name = "${var.project}/${local.environment}/backend/runtime-env-json"
  redis_url                   = "rediss://${module.valkey.primary_endpoint_address}:${module.valkey.port}/0"
}

module "ecr" {
  source      = "../../modules/ecr"
  environment = local.environment
  project     = var.project
}

module "network" {
  source      = "../../modules/network"
  environment = local.environment
  project     = var.project
  vpc_cidr    = var.vpc_cidr
}

module "secrets" {
  source                      = "../../modules/secrets"
  backend_runtime_secret_name = local.backend_runtime_secret_name
}

module "valkey" {
  source            = "../../modules/valkey"
  environment       = local.environment
  project           = var.project
  subnet_ids        = module.network.private_subnet_ids
  security_group_id = module.network.valkey_security_group_id
  node_type         = var.valkey_node_type
}

module "apprunner" {
  source                     = "../../modules/apprunner"
  environment                = local.environment
  project                    = var.project
  image_uri                  = local.backend_image
  backend_runtime_secret_arn = module.secrets.backend_runtime_secret_arn
  private_subnet_ids         = module.network.private_subnet_ids
  security_group_ids         = [module.network.apprunner_security_group_id]
  cpu                        = var.apprunner_cpu
  memory                     = var.apprunner_memory
  redis_url                  = local.redis_url
}

module "apigw" {
  source        = "../../modules/apigw"
  environment   = local.environment
  project       = var.project
  apprunner_url = "https://${module.apprunner.service_url}"
}

module "ws_realtime" {
  source            = "../../modules/ws_realtime"
  environment       = local.environment
  project           = var.project
  http_api_base_url = module.apigw.api_endpoint
}

module "ecs_celery" {
  source                     = "../../modules/ecs_celery"
  environment                = local.environment
  project                    = var.project
  image_uri                  = local.backend_image
  private_subnet_ids         = module.network.private_subnet_ids
  security_group_id          = module.network.ecs_security_group_id
  backend_runtime_secret_arn = module.secrets.backend_runtime_secret_arn
  worker_desired_count       = var.worker_desired_count
  redis_url                  = local.redis_url
  ws_connections_table_name  = module.ws_realtime.connections_table_name
  ws_connections_table_arn   = module.ws_realtime.connections_table_arn
  ws_management_api_endpoint = module.ws_realtime.management_api_endpoint
  ws_management_api_arn      = module.ws_realtime.websocket_execution_arn
}

module "frontend_static" {
  source      = "../../modules/frontend_static"
  environment = local.environment
  project     = var.project
}
