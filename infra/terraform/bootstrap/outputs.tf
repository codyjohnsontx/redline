output "project_id" {
  description = "ID of the lab project."
  value       = google_project.lab.project_id
}

output "state_bucket" {
  description = "Bucket holding Terraform state for both roots; pass it to terraform init as -backend-config=\"bucket=...\"."
  value       = google_storage_bucket.tfstate.name
}

output "budget_name" {
  description = "Resource name of the monthly budget."
  value       = google_billing_budget.lab.name
}

output "workload_identity_provider" {
  description = "Full provider name for google-github-actions/auth's workload_identity_provider input."
  value       = google_iam_workload_identity_pool_provider.github.name
}
