resource "google_monitoring_notification_channel" "owner_email" {
  provider = google.quota

  project      = google_project.lab.project_id
  display_name = "Redline owner email"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }

  depends_on = [google_project_service.bootstrap]
}

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

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.owner_email.id]
    # Billing account administrators keep receiving the default emails too.
    disable_default_iam_recipients = false
  }

  depends_on = [google_project_service.bootstrap]
}
