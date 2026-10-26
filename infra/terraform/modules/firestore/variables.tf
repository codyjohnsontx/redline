variable "project_id" {
  description = "Project that owns the database."
  type        = string
}

variable "location" {
  description = "Database location. It cannot be changed after creation."
  type        = string
}
