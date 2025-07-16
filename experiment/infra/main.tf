resource "google_service_account" "gce_sa" {
  account_id   = "container-vm-sa"
  display_name = "Service Account for Container VM"
}

resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gce_sa.email}"
}

module "cluster" {
  count = length(var.experiment_type_per_cluster)

  source = "./modules/cluster"

  run = local.group_ids[count.index]

  gce_sa_email = google_service_account.gce_sa.email

  cluster_size   = var.cluster_size
  project_id     = var.project_id
  experiment_dir = var.experiment_dir

  server_cmds     = var.server_cmds_per_cluster[count.index]
  client_cmd      = var.client_cmd_per_cluster[count.index]
  experiment_type = var.experiment_type_per_cluster[count.index]
}

