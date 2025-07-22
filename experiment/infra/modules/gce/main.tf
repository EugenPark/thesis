module "container" {
  source  = "terraform-google-modules/container-vm/google"
  version = "~> 3.0"

  container = {
    image   = "us-central1-docker.pkg.dev/${var.project_id}/docker-registry/crdb-experiment-${var.experiment_type}"
    command = var.cmd

    volumeMounts = [
      {
        mountPath = var.experiment_dir
        name      = "experiment"
        readOnly  = false
      }
    ]
  }

  volumes = [
    {
      name = "experiment"
      hostPath = {
        path = var.remote_dir
        type = "DirectoryOrCreate"
      }
    }
  ]

  restart_policy = "Never"
}

resource "google_compute_instance" "gce" {
  name                      = var.name
  machine_type              = var.gce_spec
  zone                      = "us-central1-a"
  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = "projects/cos-cloud/global/images/family/cos-stable"
      size  = 30
      type  = var.disk_type
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata = {
    ssh-keys                  = "epark:${file("~/.ssh/google_compute_engine.pub")}"
    gce-container-declaration = module.container.metadata_value
  }

  service_account {
    email = var.gce_sa_email
    scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }
}
