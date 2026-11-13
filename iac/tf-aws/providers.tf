provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "kawal-siber"
      Component   = "single-ec2"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}
