resource "google_service_account" "build" {
  account_id   = "${local.service_name}-build"
  display_name = "Briefolio Ingest Build"

  depends_on = [google_project_service.iam]
}

resource "google_service_account" "runtime" {
  account_id   = "${local.service_name}-runtime"
  display_name = "Briefolio Ingest Runtime"

  depends_on = [google_project_service.iam]
}

resource "google_service_account" "scheduler" {
  account_id   = "${local.service_name}-scheduler"
  display_name = "Briefolio Ingest Scheduler"

  depends_on = [google_project_service.iam]
}

# Build SA: start and run triggered builds, push images, deploy Cloud Run with the runtime SA, and write build logs.
resource "google_project_iam_member" "build_creator" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.build.email}"
}

resource "google_service_account_iam_member" "build_self_user" {
  service_account_id = google_service_account.build.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.build.email}"
}

resource "google_artifact_registry_repository_iam_member" "build_image_writer" {
  location   = google_artifact_registry_repository.container.location
  repository = google_artifact_registry_repository.container.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.build.email}"
}

resource "google_cloud_run_v2_service_iam_member" "build_deployer" {
  location = google_cloud_run_v2_service.app.location
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.build.email}"
}

resource "google_service_account_iam_member" "build_runtime_user" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.build.email}"
}

resource "google_project_iam_member" "build_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.build.email}"
}

# Runtime SA: read and write Firestore dedup state and create raw capture objects.
resource "google_project_iam_member" "runtime_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "runtime_object_creator" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# Scheduler SA: invoke the authenticated Cloud Run service with OIDC.
resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  location = google_cloud_run_v2_service.app.location
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
