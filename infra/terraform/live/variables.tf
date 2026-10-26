variable "project_id" {
  description = "ID of the lab project that bootstrap created."
  type        = string
}

variable "region" {
  description = "Region for regional resources. Gemini itself is called on the global endpoint."
  type        = string
  default     = "us-central1"
}

variable "github_repository" {
  description = "GitHub repository (owner/name) whose workflows may impersonate the CI service account. Must match bootstrap."
  type        = string
  default     = "codyjohnsontx/redline"
}

variable "workload_identity_pool_id" {
  description = "ID of the workload identity pool that bootstrap created."
  type        = string
  default     = "github"
}

variable "recaptcha_domains" {
  description = "Domains allowed to use the playground's reCAPTCHA key. Subdomains are allowed automatically."
  type        = list(string)
  default     = ["redline.cody-johnson.com", "localhost"]
}
