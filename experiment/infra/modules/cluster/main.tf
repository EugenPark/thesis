locals {
  name_prefix = "experiment-${var.run}-${var.experiment_type}"
}

module "servers" {
  count           = var.cluster_size
  source          = "../gce"
  name            = "${local.name_prefix}-server-${count.index + 1}"
  gce_spec        = "e2-standard-4"
  disk_type       = "pd-standard"
  gce_sa_email    = var.gce_sa_email
  cmd             = var.server_cmds[count.index]
  project_id      = var.project_id
  experiment_type = var.experiment_type
  experiment_dir  = var.experiment_dir
}

module "client" {
  source          = "../gce"
  name            = "${local.name_prefix}-client"
  gce_spec        = "e2-standard-2"
  gce_sa_email    = var.gce_sa_email
  cmd             = var.client_cmd
  project_id      = var.project_id
  experiment_type = var.experiment_type
  experiment_dir  = var.experiment_dir

  depends_on = [module.servers]
}
