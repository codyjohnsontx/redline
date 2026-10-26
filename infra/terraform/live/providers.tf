# The owner runs this root with user Application Default Credentials. Several
# APIs (reCAPTCHA Enterprise among them) refuse user credentials unless the
# request names a quota project, so every request names the lab project.
provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
