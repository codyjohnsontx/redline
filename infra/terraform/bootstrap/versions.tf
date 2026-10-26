terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.8"
    }
  }

  # The bucket is passed at init time (-backend-config="bucket=..."), so no
  # project-specific name is committed. The first apply runs with local state;
  # see infra/terraform/README.md for the one-time migration into the bucket.
  backend "gcs" {
    prefix = "bootstrap"
  }
}
