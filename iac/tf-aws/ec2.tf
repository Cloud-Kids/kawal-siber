# ==============================================================================
# EC2 — the ONLY compute resource. One Ubuntu 24.04 LTS instance running the
# full KAWAL SIBER stack via Docker Compose (deploy/single-instance/).
#
# user_data only prepares the host (Docker Engine + Compose plugin + dirs).
# It contains NO secrets, NO credentials, NO application deployment logic.
# ==============================================================================

resource "aws_instance" "kawal_siber" {
  ami                    = data.aws_ami.ubuntu_2404.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.kawal_siber.id]

  associate_public_ip_address = var.associate_public_ip

  user_data = templatefile("${path.module}/templates/ec2-user-data.sh.tftpl", {
    instance_name = var.instance_name
  })

  # Root EBS volume — inline block, no separate volume/attachment resource.
  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = var.root_volume_encrypted
    delete_on_termination = var.delete_on_termination
  }

  # Sensible lifecycle: replace on AMI drift, terminate before create.
  lifecycle {
    create_before_destroy = false
  }

  tags = merge(local.instance_tags, {
    Name = var.instance_name
  })
}
