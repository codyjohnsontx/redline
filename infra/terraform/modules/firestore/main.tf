# The (default) database: named databases get no free quota.
resource "google_firestore_database" "this" {
  project          = var.project_id
  name             = "(default)"
  location_id      = var.location
  type             = "FIRESTORE_NATIVE"
  database_edition = "STANDARD"

  # Interactions are kept (plan section 5), so the database must not be
  # deletable by accident, from Terraform or the console.
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "ABANDON"
}
