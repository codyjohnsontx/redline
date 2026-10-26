resource "google_project" "lab" {
  project_id      = var.project_id
  name            = var.project_name
  billing_account = var.billing_account

  # A destroy of this root must never delete the project.
  deletion_policy = "PREVENT"
}

# APIs the bootstrap and live roots manage resources through. APIs used only
# by the lab's resources themselves are enabled in live, next to them.
locals {
  bootstrap_services = [
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ]
}

resource "google_project_service" "bootstrap" {
  for_each = toset(local.bootstrap_services)

  project            = google_project.lab.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "tfstate" {
  project  = google_project.lab.project_id
  name     = "${var.project_id}-tfstate"
  location = var.region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  deletion_policy             = "PREVENT"

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.bootstrap]
}
