output "api_base_url" {
  value = module.apigw.api_endpoint
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
