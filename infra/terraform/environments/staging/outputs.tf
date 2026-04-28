output "api_base_url" {
  value = module.apigw.api_endpoint
}

output "api_v1_base_url" {
  value = "${module.apigw.api_endpoint}/api/v1"
}

output "frontend_base_url" {
  value = "https://${module.frontend_static.cloudfront_domain_name}"
}

output "apprunner_service_url" {
  value = "https://${module.apprunner.service_url}"
}

output "websocket_url" {
  value = module.ws_realtime.websocket_url
}

output "frontend_bucket_name" {
  value = module.frontend_static.bucket_name
}

output "frontend_cloudfront_distribution_id" {
  value = module.frontend_static.cloudfront_distribution_id
}

output "frontend_cloudfront_domain_name" {
  value = module.frontend_static.cloudfront_domain_name
}

output "backend_ecr_repository_url" {
  value = module.ecr.backend_repository_url
}

output "backend_runtime_secret_arn" {
  value     = module.secrets.backend_runtime_secret_arn
  sensitive = true
}

# Same value App Runner receives as REDIS_URL (for GitHub Actions db-migrate, etc.).
output "redis_url" {
  value       = local.redis_url
  sensitive   = true
  description = "Valkey primary URL (same as App Runner REDIS_URL); deploy-aws db-migrate reads this from state."
}

output "links" {
  value = {
    api_health                  = "${module.apigw.api_endpoint}/health"
    apprunner_service           = "https://${var.aws_region}.console.aws.amazon.com/apprunner/home?region=${var.aws_region}#/services/${module.apprunner.service_arn}"
    api_gateway_routes          = "https://${var.aws_region}.console.aws.amazon.com/apigateway/main/apis/${module.apigw.api_id}/routes?api=${module.apigw.api_id}&region=${var.aws_region}"
    websocket_api               = "https://${var.aws_region}.console.aws.amazon.com/apigateway/main/apis/${module.ws_realtime.websocket_api_id}/routes?api=${module.ws_realtime.websocket_api_id}&region=${var.aws_region}"
    websocket_url               = module.ws_realtime.websocket_url
    websocket_connections_table = "https://${var.aws_region}.console.aws.amazon.com/dynamodbv2/home?region=${var.aws_region}#table?name=${module.ws_realtime.connections_table_name}"
    cloudfront_distribution     = "https://us-east-1.console.aws.amazon.com/cloudfront/v4/home#/distributions/${module.frontend_static.cloudfront_distribution_id}"
    frontend_site               = "https://${module.frontend_static.cloudfront_domain_name}"
    frontend_bucket             = "https://s3.console.aws.amazon.com/s3/buckets/${module.frontend_static.bucket_name}?region=${var.aws_region}&bucketType=general"
    ecs_cluster                 = "https://${var.aws_region}.console.aws.amazon.com/ecs/v2/clusters/${module.ecs_celery.cluster_name}/services?region=${var.aws_region}"
    ecs_worker_service          = "https://${var.aws_region}.console.aws.amazon.com/ecs/v2/clusters/${module.ecs_celery.cluster_name}/services/${module.ecs_celery.worker_service_name}/health?region=${var.aws_region}"
    ecs_beat_service            = "https://${var.aws_region}.console.aws.amazon.com/ecs/v2/clusters/${module.ecs_celery.cluster_name}/services/${module.ecs_celery.beat_service_name}/health?region=${var.aws_region}"
    worker_logs                 = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/${urlencode(module.ecs_celery.worker_log_group_name)}"
    beat_logs                   = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/${urlencode(module.ecs_celery.beat_log_group_name)}"
    valkey_replication_group    = "https://${var.aws_region}.console.aws.amazon.com/elasticache/home?region=${var.aws_region}#redis:replicationGroups/${module.valkey.replication_group_id}"
    ecr_repository              = "https://${var.aws_region}.console.aws.amazon.com/ecr/repositories/private/${replace(module.ecr.backend_repository_url, "${split("/", module.ecr.backend_repository_url)[0]}/", "")}?region=${var.aws_region}"
    secrets_manager             = "https://${var.aws_region}.console.aws.amazon.com/secretsmanager/listsecrets?region=${var.aws_region}"
  }
}
