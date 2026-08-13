resource "google_cloud_run_v2_service" "app" {
  name     = "${local.service_name}-app"
  location = var.region

  # Same-project Cloud Scheduler calls to the default run.app URL count as internal traffic.
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.runtime.email
    timeout         = "600s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      # Placeholder for creation; Cloud Build deploys the image for each triggered main-branch commit.
      image = local.bootstrap_image

      env {
        name  = "RAW_BUCKET_NAME"
        value = google_storage_bucket.raw.name
      }

      resources {
        cpu_idle          = true
        startup_cpu_boost = true
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Cloud Build owns post-creation image updates; Terraform preserves them during in-place updates.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [google_project_service.run]
}
