module "container" {
  count   = var.cluster_size
  source  = "terraform-google-modules/container-vm/google"
  version = "~> 3.0"

  cos_image_name = "cos-stable-77-12371-89-0"

  container = {
    image   = "us-central1-docker.pkg.dev/${var.project_id}/docker-registry/crdb-experiment-${var.experiment_type}"
    command = var.experiment_commands[count.index]

    volumeMounts = [
      {
        mountPath = "/var/experiment/data"
        name      = "data"
        readOnly  = false
      },
      {
        mountPath = "/var/experiment/logs"
        name      = "logs"
        readOnly  = false
      }
    ]
  }

  volumes = [
    {
      name = "data"
      hostPath = {
        path = "/var/experiment/data"
        type = "DirectoryOrCreate"
      }
    },
    {
      name = "logs"
      hostPath = {
        path = "/var/experiment/logs"
        type = "DirectoryOrCreate"
      }
    }
  ]

  restart_policy = "Never"
}

resource "google_compute_instance" "gce" {
  count                     = var.cluster_size
  name                      = "${var.gce_type}-${count.index + 1}"
  machine_type              = var.gce_specs[count.index]
  zone                      = "us-central1-a"
  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = "projects/cos-cloud/global/images/family/cos-stable"
      size  = 10
      type  = var.disk_types[count.index]
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys                  = "epark:${file("~/.ssh/google_compute_engine.pub")}"
    gce-container-declaration = module.container[count.index].metadata_value
  }

  service_account {
    email = var.gce_sa_email
    scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }
}
