variable "cluster_size" {
  type        = number
  description = "Number of nodes in the cluster"
}

variable "gce_type" {
  type        = string
  description = "Set either server or client"
  validation {
    condition     = contains(["server", "client"], var.gce_type)
    error_message = "The environment must be either 'server' or 'client'."
  }
}

variable "gce_specs" {
  type        = list(string)
  default     = ["e2-medium", "e2-medium", "e2-medium"]
  description = "Which specs to spin up default is ['e2-medium', 'e2-medium', 'e2-medium']"
}

variable "gce_sa_email" {
  type        = string
  description = "Email address of service account to be able to read from artifact registry"
}

variable "disk_types" {
  type        = list(string)
  default     = ["pd-standard", "pd-standard", "pd-standard"]
  description = "Persistent Disk Type valid options are pd-standard, pd-balanced, pd-ssd"
}

variable "experiment_type" {
  type        = string
  default     = "baseline"
  description = "The type of experiment. Could be either baseline or thesis"
}

variable "experiment_commands" {
  type        = list(string)
  description = "The commands to be executed in the container"
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}
