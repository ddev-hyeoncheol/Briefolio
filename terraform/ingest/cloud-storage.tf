resource "google_storage_bucket" "raw" {
  name     = "${var.project_id}-raw"
  location = var.region

  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  depends_on = [google_project_service.storage]
}
