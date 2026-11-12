terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Local state only — no S3 backend.
  # WARNING: terraform.tfstate may contain sensitive infrastructure
  # information (instance IDs, public IPs, key pair names). Protect it with
  # filesystem permissions and keep an offline backup. Do NOT commit it.
}
