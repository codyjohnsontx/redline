output "email" {
  description = "Email of the service account."
  value       = google_service_account.this.email
}

output "name" {
  description = "Full resource name, for service-account-level IAM bindings."
  value       = google_service_account.this.name
}

output "member" {
  description = "IAM member string (serviceAccount:<email>)."
  value       = google_service_account.this.member
}
