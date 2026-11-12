# ==============================================================================
# Security Group — the ONLY network access control resource.
#
# Inbound : SSH 22 (admin_cidr only), HTTP 80 + HTTPS 443 (web_allowed_cidrs).
# Outbound: all egress (required for apt, Docker Hub, GitHub, image registries,
#           and ACME/Let's Encrypt certificate issuance on the host).
#
# Internal application ports (3000, 8000, 5432, 6379, 9100, 11434) are NEVER
# published — the Nginx/Caddy reverse proxy container is the only public ingress.
# ==============================================================================

resource "aws_security_group" "kawal_siber" {
  name        = "${var.instance_name}-sg"
  description = "KAWAL SIBER single-EC2: SSH admin + web 80/443 only"
  vpc_id      = var.vpc_id

  # --- SSH: administrator access only ---------------------------------------
  ingress {
    description = "SSH from administrator CIDR only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  # --- Web: HTTP/HTTPS from allowed web CIDRs -------------------------------
  dynamic "ingress" {
    for_each = toset(local.effective_web_cidrs)
    content {
      description = "HTTP from allowed web CIDR"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  dynamic "ingress" {
    for_each = toset(local.effective_web_cidrs)
    content {
      description = "HTTPS from allowed web CIDR"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # --- Outbound: unrestricted egress for package/image/cert operations ------
  egress {
    description = "All outbound (apt, Docker Hub, GitHub, registries, ACME)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.instance_tags, { Name = "${var.instance_name}-sg" })
}

# ==============================================================================
# Pre-flight validation of the EXISTING network — fails fast with a clear
# message instead of silently provisioning anything.
# ==============================================================================

check "subnet_belongs_to_vpc" {
  assert {
    condition     = data.aws_subnet.selected.vpc_id == var.vpc_id
    error_message = "subnet_id ${var.subnet_id} does not belong to vpc_id ${var.vpc_id}. Pick a subnet inside the selected VPC (AWS Console → VPC → Subnets)."
  }
}

check "subnet_is_public" {
  assert {
    condition     = data.aws_subnet.selected.map_public_ip_on_launch
    error_message = "subnet_id ${var.subnet_id} does not auto-assign public IPs. Choose a public subnet (route table with 0.0.0.0/0 → igw-*) or set associate_public_ip = true is already enabled — verify the subnet has an Internet Gateway route."
  }
}
