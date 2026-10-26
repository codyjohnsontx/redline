# Least privilege per workload (plan section 6.3). Accounts whose every grant
# targets a resource a later PR creates (budget-guard, scheduler, the deploy
# account for main) arrive with that PR, so no account here holds a role it
# cannot use yet. Access to the session-signing and Anthropic secrets is
# granted on each secret when it is created.

module "sa_playground" {
  source = "../modules/service-account"

  project_id   = var.project_id
  account_id   = "sa-playground"
  display_name = "Playground API"
  description  = "Cloud Run service behind the public playground."
  project_roles = [
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/modelarmor.user",
    "roles/monitoring.metricWriter",
    "roles/recaptchaenterprise.agent",
  ]
}

module "sa_eval_runner" {
  source = "../modules/service-account"

  project_id   = var.project_id
  account_id   = "sa-eval-runner"
  display_name = "Eval runner"
  description  = "Cloud Run job that runs the weekly full eval."
  project_roles = [
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

module "sa_github_ci" {
  source = "../modules/service-account"

  project_id   = var.project_id
  account_id   = "sa-github-ci"
  display_name = "GitHub Actions CI"
  description  = "Per-PR fast-slice eval from any branch of the repository."
  project_roles = [
    "roles/aiplatform.user",
  ]
}

resource "google_storage_bucket_iam_member" "results_eval_runner" {
  bucket = google_storage_bucket.results.name
  role   = "roles/storage.objectAdmin"
  member = module.sa_eval_runner.member
}

resource "google_storage_bucket_iam_member" "results_github_ci" {
  bucket = google_storage_bucket.results.name
  role   = "roles/storage.objectViewer"
  member = module.sa_github_ci.member
}

# Any workflow run in the repository may act as the CI account. The pool's
# provider already rejects tokens from every other repository.
resource "google_service_account_iam_member" "github_ci_wif" {
  service_account_id = module.sa_github_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.lab.number}/locations/global/workloadIdentityPools/${var.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
