# ==============================================================================
# Data sources — READ-ONLY lookups. These create NO AWS infrastructure.
# ==============================================================================

# Latest official Canonical Ubuntu Server 24.04 LTS HVM SSD AMD64 image.
# Owner 099720109477 is Canonical's official AWS account ID.
data "aws_ami" "ubuntu_2404" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Existing VPC — validated against the subnet below.
data "aws_vpc" "selected" {
  id = var.vpc_id
}

# Existing public subnet — must belong to var.vpc_id.
data "aws_subnet" "selected" {
  id = var.subnet_id
}
