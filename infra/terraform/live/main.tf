data "google_project" "lab" {
  project_id = var.project_id
}

# APIs the lab's own resources need. Later PRs add theirs here (Cloud Run,
# Artifact Registry, Secret Manager, Pub/Sub, Scheduler, Firebase Hosting).
locals {
  services = [
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "firestore.googleapis.com",
    "logging.googleapis.com",
    "modelarmor.googleapis.com",
    "monitoring.googleapis.com",
    "recaptchaenterprise.googleapis.com",
  ]
}

resource "google_project_service" "lab" {
  for_each = toset(local.services)

  service            = each.value
  disable_on_destroy = false
}

module "model_armor" {
  source = "../modules/model-armor"

  project_id  = var.project_id
  location    = var.region
  template_id = "fh-playground"

  depends_on = [google_project_service.lab]
}

module "firestore" {
  source = "../modules/firestore"

  project_id = var.project_id
  location   = var.region

  depends_on = [google_project_service.lab]
}

# Score-based key for the playground's bot check: one assessment per new
# session, not per message (plan section 7).
resource "google_recaptcha_enterprise_key" "playground" {
  display_name = "redline-playground"

  web_settings {
    integration_type  = "SCORE"
    allowed_domains   = var.recaptcha_domains
    allow_amp_traffic = false
  }

  depends_on = [google_project_service.lab]
}

# Private results: the unpublished test split, eval run outputs, judgment
# cache shards, and main's baseline for the CI gate.
resource "google_storage_bucket" "results" {
  name     = "${var.project_id}-results"
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  deletion_policy             = "PREVENT"

  versioning {
    enabled = true
  }
}
