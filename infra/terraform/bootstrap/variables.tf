variable "billing_account" {
  description = "ID of the owner's existing Cloud Billing account (XXXXXX-XXXXXX-XXXXXX)."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-Z]{6}-[0-9A-Z]{6}-[0-9A-Z]{6}$", var.billing_account))
    error_message = "billing_account must look like XXXXXX-XXXXXX-XXXXXX."
  }
}

variable "project_id" {
  description = "ID of the project to create. Project IDs are global, so add a suffix (for example redline-lab-4821)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be 6-30 characters: lowercase letters, digits, and hyphens, starting with a letter."
  }
}

variable "project_name" {
  description = "Display name of the project."
  type        = string
  default     = "Redline Lab"
}

variable "region" {
  description = "Region for regional resources."
  type        = string
  default     = "us-central1"
}

variable "monthly_budget_usd" {
  description = "Monthly budget for the project in whole US dollars."
  type        = number
  default     = 25
}

variable "github_repository" {
  description = "GitHub repository (owner/name) whose Actions workflows may federate into the project."
  type        = string
  default     = "codyjohnsontx/redline"
}

variable "github_repository_id" {
  description = "Numeric ID of the GitHub repository. Pinning the immutable ID stops a recreated repository with the same name from federating."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must be the numeric repository ID."
  }
}

variable "github_repository_owner_id" {
  description = "Numeric ID of the GitHub account that owns the repository."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must be the numeric account ID."
  }
}
