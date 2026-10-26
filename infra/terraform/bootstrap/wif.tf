# Workload Identity Federation for GitHub Actions: workflows in the one
# repository exchange their OIDC token for short-lived Google credentials, so
# no service account key is ever stored. Which service accounts a workflow may
# impersonate is granted in live, per account.
resource "google_iam_workload_identity_pool" "github" {
  project                   = google_project.lab.project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "GitHub Actions workflows in ${var.github_repository}"

  depends_on = [google_project_service.bootstrap]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = google_project.lab.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions OIDC"
  description                        = "Tokens from ${var.github_repository} only"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Tokens from any other repository or owner are rejected outright. The
  # numeric IDs are immutable, unlike the owner/name string.
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${var.github_repository_id}'",
    "assertion.repository_owner_id == '${var.github_repository_owner_id}'",
    "assertion.repository == '${var.github_repository}'",
  ])

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}
