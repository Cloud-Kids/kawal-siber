locals {
  # Web ingress falls back to the admin CIDR when no explicit list is given,
  # so initial private testing is never wide open by accident.
  effective_web_cidrs = length(var.web_allowed_cidrs) > 0 ? var.web_allowed_cidrs : [var.admin_cidr]

  instance_tags = {
    Name        = var.instance_name
    Project     = "kawal-siber"
    Component   = "single-ec2"
    Environment = var.environment
  }
}
