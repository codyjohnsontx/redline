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
