#!/usr/bin/env bash
set -euo pipefail

# One-time manual bootstrap for the Briefolio Seed project.
# The remote backend bucket must exist before the Terraform roots are initialized,
# so this script runs outside Terraform.

PROJECT_ID="briefolio-seed"
BUCKET="briefolio-tfstate"
REGION="us-west1"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is required." >&2
  exit 1
fi

if [[ -z "$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)" ]]; then
  echo "Run 'gcloud auth login' before this script." >&2
  exit 1
fi

# 1. Ensure the Briefolio Seed project exists.
if ! gcloud projects describe "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud projects create "${PROJECT_ID}" --name="Briefolio Seed"
fi

# 2. Manual prerequisite for new projects: link the intended billing account.
# gcloud billing accounts list
# gcloud billing projects link "${PROJECT_ID}" --billing-account=<BILLING_ACCOUNT_ID>

# 3. Enable Cloud Storage before managing the state bucket.
gcloud services enable storage.googleapis.com --project="${PROJECT_ID}"

# 4. Ensure the Terraform state bucket exists.
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --public-access-prevention
fi

# 5. Preserve state history and enforce bucket-level, non-public access on every run.
gcloud storage buckets update "gs://${BUCKET}" \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --versioning
