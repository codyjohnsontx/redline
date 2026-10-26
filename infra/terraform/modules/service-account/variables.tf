variable "project_id" {
  description = "Project the service account lives in and receives roles on."
  type        = string
}

variable "account_id" {
  description = "Account ID, the part of the email before the @."
  type        = string
}

variable "display_name" {
  description = "Display name of the service account."
  type        = string
}

variable "description" {
  description = "What runs as this service account."
  type        = string
}

variable "project_roles" {
  description = "Roles granted on the whole project, such as roles/aiplatform.user."
  type        = list(string)
  default     = []
}
