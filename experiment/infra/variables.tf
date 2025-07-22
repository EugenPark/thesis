variable "server_cmds" {
  type = list(list(string))
}

variable "client_cmd" {
  type = list(string)
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
  description = "The directory where the experiment shall be saved to in the container"
}

variable "experiment_type" {
  type        = string
  description = "The type of experiment. Should be either baseline or thesis"
  validation {
    condition     = contains(["baseline", "thesis"], var.experiment_type)
    error_message = "The experiment_type must be one of [baseline, thesis]"
  }
}


variable "remote_dir" {
  type        = string
  description = "The directory where the experiment is saved to on the machine"
}
