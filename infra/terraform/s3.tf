# The single data-lake bucket. Zones (raw/curated/features/models/athena-results) are prefixes within it - see doc/data_lake_layout.md

resource "aws_s3_bucket" "data_lake" {
    bucket = var.bucket_name

    tags = {
        Project = "dc-gpu-workload-platform"
    }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "data_lake" {
    bucket = aws_s3_bucket.data_lake.id

    block_public_acls = true
    block_public_policy = true
    ignore_public_acls = true
    restrict_public_buckets = true
}

# Default server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
    bucket = aws_s3_bucket.data_lake.id

    rule {
        apply_server_side_encryption_by_default {
            sse_algorithm = "AES256"
        }
    }
}

# Versioning off by default: the replay producer writes to new date-paritioned keys rather than overwriting, so there's little to protect by versioning, and it avoids extra storage for old versions
resource "aws_s3_bucket_versioning" "data_lake" {
    bucket = aws_s3_bucket.data_lake.id

    versioning_configuration {
        status = "Disabled"
    }
}

# Athena writes a results file on every query; without this the athena-results/ prefix grows forever for no benefit
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
    bucket = aws_s3_bucket.data_lake.id

    rule {
        id = "expire-athena-query-results"
        status = "Enabled"

        filter {
            prefix = "athena-results/"
        }

        expiration {
            days = 7
        }
    }
}