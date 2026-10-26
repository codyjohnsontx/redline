terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.8"
    }
  }

  # Same bucket as bootstrap, passed at init time: -backend-config="bucket=..."
  backend "gcs" {
    prefix = "live"
  }
}
