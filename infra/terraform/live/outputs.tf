output "model_armor_template" {
  description = "Full name of the playground's Model Armor template."
  value       = module.model_armor.name
}

output "firestore_database" {
  description = "Firestore database ID."
  value       = module.firestore.name
}

output "recaptcha_site_key" {
  description = "reCAPTCHA site key. It is public by design: the page embeds it."
  value       = google_recaptcha_enterprise_key.playground.name
}

output "results_bucket" {
  description = "Private results bucket."
  value       = google_storage_bucket.results.name
}

output "service_accounts" {
  description = "Service account emails by workload."
  value = {
    playground  = module.sa_playground.email
    eval_runner = module.sa_eval_runner.email
    github_ci   = module.sa_github_ci.email
  }
}
