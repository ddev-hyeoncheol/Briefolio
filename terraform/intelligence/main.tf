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
    prefix = "intelligence"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name = "intelligence"
}

variable "project_id" {
  description = "Google Cloud project ID that owns the Briefolio Intelligence resources."
  type        = string
  default     = "briefolio-intelligence"
  nullable    = false
}

variable "region" {
  description = "Google Cloud region used by regional Briefolio Intelligence resources."
  type        = string
  default     = "us-west1"
  nullable    = false
}
