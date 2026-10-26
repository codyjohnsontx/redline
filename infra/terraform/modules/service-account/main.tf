resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
}

# Project-wide roles only. Grants on a single resource (a bucket, a secret)
# belong next to that resource, so this list stays the short one.
resource "google_project_iam_member" "this" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = google_service_account.this.member
}
