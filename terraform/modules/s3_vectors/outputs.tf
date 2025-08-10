output "bucket_name" {
  value = "alex-vectors-${var.aws_account_id}"
}

output "bucket_arn" {
  value = "arn:aws:s3:::alex-vectors-${var.aws_account_id}"
}