provider "google" {
  region = var.region
}

# The Billing Budgets API refuses user Application Default Credentials unless
# requests name a quota project. The lab project serves as that quota project
# once it exists and has the API enabled.
provider "google" {
  alias                 = "quota"
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
