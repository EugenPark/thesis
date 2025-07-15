resource "google_service_account" "gce_sa" {
  account_id   = "container-vm-sa"
  display_name = "Service Account for Container VM"
}

resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gce_sa.email}"
}

module "servers" {
  count           = var.cluster_size
  source          = "./modules/gce"
  name            = "server-${count.index + 1}"
  gce_spec        = "e2-standard-4"
  disk_type       = "pd-standard"
  gce_sa_email    = google_service_account.gce_sa.email
  cmd             = local.server_cmds[count.index]
  project_id      = var.project_id
  experiment_type = var.experiment_type
  experiment_dir  = var.experiment_dir
}

module "client" {
  source          = "./modules/gce"
  name            = "client"
  gce_spec        = "e2-standard-2"
  gce_sa_email    = google_service_account.gce_sa.email
  cmd             = local.client_cmd
  project_id      = var.project_id
  experiment_type = var.experiment_type
  experiment_dir  = var.experiment_dir

  depends_on = [module.servers]
}
