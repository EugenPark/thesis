variable "server_cmds_per_cluster" {
  type = list(list(list(string)))
}

variable "client_cmd_per_cluster" {
  type = list(list(string))
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "cluster_size" {
  type        = number
  description = "Cluster size of the nodes spun up"
}

variable "experiment_dir" {
  type        = string
  description = "The directory where the experiment shall be saved to"
}

variable "experiment_type_per_cluster" {
  type        = list(string)
  description = "The type of experiment. Should be either baseline or thesis"
}

locals {
  unique_values = distinct(var.experiment_type_per_cluster)
  chunk_size    = length(local.unique_values)
  total_items   = length(var.experiment_type_per_cluster)

  # Generate indices [0, 1, 2, ..., total_items - 1]
  indices = range(local.total_items)

  # Chunked group ids: floor(i / chunk_size) + 1
  group_ids = [for i in local.indices : floor(i / local.chunk_size) + 1]
}
