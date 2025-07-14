resource "google_service_account" "gce_sa" {
  account_id   = "container-vm-sa"
  display_name = "Service Account for Container VM"
}

resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gce_sa.email}"
}

# TODO: unify cluster size and the specs and disk types
module "server" {
  source              = "./modules/gce"
  gce_type            = "server"
  gce_specs           = ["e2-standard-4", "e2-standard-4", "e2-standard-4", "e2-standard-4", "e2-standard-4"]
  disk_types          = ["pd-standard", "pd-standard", "pd-standard", "pd-standard", "pd-standard"]
  gce_sa_email        = google_service_account.gce_sa.email
  experiment_commands = var.server_cmds
  project_id          = var.project_id
  cluster_size        = var.cluster_size
}

module "client" {
  source              = "./modules/gce"
  gce_type            = "client"
  gce_specs           = ["e2-standard-2"]
  gce_sa_email        = google_service_account.gce_sa.email
  experiment_commands = [var.client_cmd]
  project_id          = var.project_id
  cluster_size        = 1
}
