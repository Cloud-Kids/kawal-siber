output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.kawal_siber.id
}

output "instance_type" {
  description = "Launched instance type"
  value       = aws_instance.kawal_siber.instance_type
}

output "public_ip" {
  description = "Public IPv4 address (use for SSH and the application URL)"
  value       = aws_instance.kawal_siber.public_ip
}

output "public_dns" {
  description = "Public DNS name of the instance"
  value       = aws_instance.kawal_siber.public_dns
}

output "private_ip" {
  description = "Private IPv4 address inside the VPC"
  value       = aws_instance.kawal_siber.private_ip
}

output "security_group_id" {
  description = "Security Group attached to the instance"
  value       = aws_security_group.kawal_siber.id
}

output "ami_id" {
  description = "AMI ID the instance was launched from"
  value       = aws_instance.kawal_siber.ami
}

output "ssh_command" {
  description = "SSH command to reach the instance (replace USER with ubuntu)"
  value       = "ssh -i <path-to-key.pem> ubuntu@${aws_instance.kawal_siber.public_ip}"
}

output "application_url" {
  description = "Application URL over HTTP. HTTPS requires a real domain + Caddy/Nginx cert on the host (see README)."
  value       = "http://${aws_instance.kawal_siber.public_ip}"
}
