terraform {
  required_version = ">= 1.7, < 2.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # The Seed project provisions this bucket before this boundary is initialized.
  backend "gcs" {
    bucket = "briefolio-tfstate"
    prefix = "ingest"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name    = "ingest"
  bootstrap_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "project_id" {
  description = "Google Cloud project ID that owns the Briefolio Ingest resources."
  type        = string
  default     = "briefolio-ingest"
  nullable    = false
}

variable "region" {
  description = "Google Cloud region used by regional Briefolio Ingest resources."
  type        = string
  default     = "us-west1"
  nullable    = false
}

variable "cloud_build_repository" {
  description = "Full resource name of the manually connected second-generation Cloud Build repository; its location must match var.region (projects/{project}/locations/{region}/connections/{connection}/repositories/{repo})."
  type        = string
  default     = "projects/briefolio-ingest/locations/us-west1/connections/github-ddev-hyeoncheol/repositories/Briefolio"
  nullable    = false
}
