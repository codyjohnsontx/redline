# Model Armor screens prompts for injection and jailbreaks before the judges
# see them (plan section 6.2). Responsible-AI filters stay off on purpose:
# hate-speech filtering ahead of the Fair Housing judge would make the judge's
# playground numbers unattributable.
resource "google_model_armor_template" "this" {
  project     = var.project_id
  location    = var.location
  template_id = var.template_id

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = var.pi_and_jailbreak_confidence
    }

    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }

    sdp_settings {
      basic_config {
        filter_enforcement = "ENABLED"
      }
    }
  }
}
