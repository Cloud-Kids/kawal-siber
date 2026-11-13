locals {
  # Web ingress falls back to the admin CIDR when no explicit list is given,
  # so initial private testing is never wide open by accident.
  # When a Cloudflare Tunnel token is configured, NO public web ports are
  # opened at all — traffic arrives via the outbound tunnel to localhost.
  tunnel_enabled      = var.cloudflare_tunnel_token != ""
  effective_web_cidrs = local.tunnel_enabled ? [] : (length(var.web_allowed_cidrs) > 0 ? var.web_allowed_cidrs : [var.admin_cidr])

  instance_tags = {
    Name        = var.instance_name
    Project     = "kawal-siber"
    Component   = "single-ec2"
    Environment = var.environment
  }
}
