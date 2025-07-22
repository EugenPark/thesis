variable "name" {
  type        = string
  description = "Name of the gce"
}

variable "gce_spec" {
  type        = string
  default     = "e2-medium"
  description = "Which specs to spin up default is 'e2-medium'"
}

variable "gce_sa_email" {
  type        = string
  description = "Email address of service account to be able to read from artifact registry"
}

variable "disk_type" {
  type        = string
  default     = "pd-standard"
  description = "Persistent Disk Type"
  validation {
    condition     = contains(["pd-standard", "pd-balanced", "pd-ssd"], var.disk_type)
    error_message = "The disk type must be one of [pd-standard, pd-balanced, pd-ssd]"
  }
}

variable "experiment_type" {
  type        = string
  description = "The type of experiment. Should be either baseline or thesis"
  validation {
    condition     = contains(["baseline", "thesis"], var.experiment_type)
    error_message = "The experiment_type must be one of [baseline, thesis]"
  }
}

variable "cmd" {
  type        = list(string)
  description = "The command to be executed in the container"
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "experiment_dir" {
  type        = string
  description = "The directory where the experiment should be written to in the container"
}

variable "remote_dir" {
  type        = string
  description = "The directory where the experiment will be save to on the machine"
}
