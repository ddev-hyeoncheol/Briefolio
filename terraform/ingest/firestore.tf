resource "google_firestore_database" "state" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  delete_protection_state = "DELETE_PROTECTION_DISABLED"
  deletion_policy         = "DELETE"

  depends_on = [google_project_service.firestore]
}

resource "google_firestore_field" "expires_at" {
  database   = google_firestore_database.state.name
  collection = "news_state"
  field      = "expires_at"

  ttl_config {}
}
