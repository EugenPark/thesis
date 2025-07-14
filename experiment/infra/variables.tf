variable "server_cmds" {
  type = list(string)
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
