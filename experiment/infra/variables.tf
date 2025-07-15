variable "server_cmds" {
  type = string
}

variable "client_cmd" {
  type = string
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

variable "experiment_type" {
  type        = string
  description = "The type of experiment. Should be either baseline or thesis"
  validation {
    condition     = contains(["baseline", "thesis"], var.experiment_type)
    error_message = "The experiment_type must be one of [baseline, thesis]"
  }
}

locals {
  server_cmds = jsondecode(var.server_cmds)
  client_cmd  = jsondecode(var.client_cmd)
}
