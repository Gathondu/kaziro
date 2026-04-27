variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "project" {
  type    = string
  default = "kaziro"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/20"
}

variable "image_tag" {
  type = string
}

variable "valkey_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "apprunner_cpu" {
  type    = string
  default = "1024"
}

variable "apprunner_memory" {
  type    = string
  default = "2048"
}

variable "worker_desired_count" {
  type    = number
  default = 1
}
