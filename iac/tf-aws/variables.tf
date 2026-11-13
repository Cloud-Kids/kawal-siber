# ==============================================================================
# KAWAL SIBER — Single-EC2 Terraform Inputs
#
# NO SECRETS BELONG IN THIS FILE OR terraform.tfvars.
# AWS Academy Learner Lab credentials are supplied via environment variables
# (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN) or an AWS
# CLI profile — never here.
# ==============================================================================

variable "aws_region" {
  description = "AWS region for the EC2 instance and Security Group (must match the region of vpc_id/subnet_id)"
  type        = string
}

variable "environment" {
  description = "Environment tag value"
  type        = string
  default     = "lab"
}

variable "instance_name" {
  description = "Name tag for the EC2 instance"
  type        = string
  default     = "kawal-siber"
}

variable "instance_type" {
  description = <<-EOT
    EC2 instance type. Default r6i.large (2 vCPU / 16 GiB) is a recommendation,
    not a guarantee — AWS Academy Learner Labs restrict allowed instance types.
    If r6i.large is unavailable, override with r5.large, r5a.large, m6i.large or
    another permitted .large type.
  EOT
  type        = string
  default     = "r6i.large"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair in the same region used for SSH access"
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC ID (e.g. the AWS Academy default VPC). Terraform does NOT create a VPC."
  type        = string
}

variable "subnet_id" {
  description = "Existing public subnet ID inside vpc_id with a route to an Internet Gateway"
  type        = string
}

variable "associate_public_ip" {
  description = "Assign a public IPv4 address to the instance (required for SSH/web access from the internet)"
  type        = bool
  default     = true
}

variable "admin_cidr" {
  description = "CIDR block allowed SSH (TCP 22) access — your current public IP, e.g. 203.0.113.10/32"
  type        = string
}

variable "web_allowed_cidrs" {
  description = "CIDR blocks allowed HTTP (80) and HTTPS (443) access. Restrict to your admin CIDR for initial private testing."
  type        = list(string)
  default     = []
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB"
  type        = number
  default     = 100
}

variable "root_volume_encrypted" {
  description = "Enable EBS encryption on the root volume where the account allows it"
  type        = bool
  default     = true
}

variable "delete_on_termination" {
  description = <<-EOT
    Delete the root volume when the instance is terminated.
    true  = terraform destroy also deletes the disk (data loss).
    false = volume persists after destroy for manual recovery.
  EOT
  type        = bool
  default     = true
}

variable "app_deploy_enabled" {
  description = "Clone the repo and start the Docker Compose stack automatically via cloud-init"
  type        = bool
  default     = true
}

variable "repo_url" {
  description = "Git URL used on the EC2 host. Use the SSH form for private repos."
  type        = string
  default     = "git@github.com:Cloud-Kids/kawal-siber.git"
}

variable "repo_branch" {
  description = "Git branch checked out on the EC2 host"
  type        = string
  default     = "main"
}
