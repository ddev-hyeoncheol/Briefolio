resource "google_cloudbuild_trigger" "deploy" {
  name            = "${local.service_name}-deploy"
  location        = var.region
  filename        = "cloudbuild.yaml"
  service_account = google_service_account.build.id

  substitutions = {
    _ARTIFACT_REPOSITORY = google_artifact_registry_repository.container.repository_id
    _IMAGE_NAME          = local.service_name
    _REGION              = var.region
    _SERVICE_NAME        = google_cloud_run_v2_service.app.name
  }

  repository_event_config {
    repository = var.cloud_build_repository

    push {
      branch = "^main$"
    }
  }

  depends_on = [google_project_service.cloudbuild]
}
