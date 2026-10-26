output "name" {
  description = "Full template name, projects/<project>/locations/<location>/templates/<id>."
  value       = google_model_armor_template.this.id
}

output "template_id" {
  description = "Template ID."
  value       = google_model_armor_template.this.template_id
}
