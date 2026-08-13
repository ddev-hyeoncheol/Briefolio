resource "google_cloud_scheduler_job" "cron" {
  name             = "${local.service_name}-cron"
  region           = var.region
  schedule         = "*/10 * * * *"
  attempt_deadline = "600s"

  # Prevent scheduled calls before the application image and endpoint are verified.
  paused = true

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.app.uri}/ingest/run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.app.uri
    }
  }

  # Operators own pause and resume after the bootstrap-safe initial state.
  lifecycle {
    ignore_changes = [paused]
  }

  depends_on = [google_project_service.cloudscheduler]
}
