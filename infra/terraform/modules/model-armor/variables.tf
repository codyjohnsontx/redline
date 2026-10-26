variable "project_id" {
  description = "Project that owns the template."
  type        = string
}

variable "location" {
  description = "Template location. Callers must use the matching regional endpoint, modelarmor.<location>.rep.googleapis.com."
  type        = string
}

variable "template_id" {
  description = "Template ID."
  type        = string
}

variable "pi_and_jailbreak_confidence" {
  description = "Lowest confidence at which the prompt injection and jailbreak filter reports a match."
  type        = string
  default     = "MEDIUM_AND_ABOVE"

  validation {
    condition     = contains(["LOW_AND_ABOVE", "MEDIUM_AND_ABOVE", "HIGH"], var.pi_and_jailbreak_confidence)
    error_message = "pi_and_jailbreak_confidence must be LOW_AND_ABOVE, MEDIUM_AND_ABOVE, or HIGH."
  }
}
