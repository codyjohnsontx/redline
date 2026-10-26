# Alerts only: a Cloud Billing budget never stops spend. The playground's own
# spend counter and kill flag stop it at the source (plan section 7).
resource "google_billing_budget" "lab" {
  provider = google.quota

  billing_account = var.billing_account
  display_name    = "${var.project_id} monthly"

  budget_filter {
    projects        = ["projects/${google_project.lab.number}"]
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  depends_on = [google_project_service.bootstrap]
}
