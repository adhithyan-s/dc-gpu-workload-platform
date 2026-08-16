variable "aws_region" {
    description = "AWS region for all resources"
    type = string
    default = "eu-west-1"
}

variable "bucket_name" {
    description = "Globally unique s3 bucket name for the delta lake. s3 bucket names are unique across ALL of AWS, not just your account - dc-gpu-workload-platform is almost certainly taken. Suggest appending your initials or a short random suffix, e.g. dc-gpu-workload-<yourname>"
    type = string
}