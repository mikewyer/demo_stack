# Demo stack for showing I can operate a terraform stack without imploding.

# PREREQ: gcloud auth application-default login

variable "gke_num_nodes" {
  default     = 1
  description = "number of gke nodes"
}

# GKE cluster
resource "google_container_cluster" "primary" {
  name     = "${var.project_id}-gke"
  location = var.region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # Follow the GCP recommendation to use VPC-Native networking
  ip_allocation_policy {
    cluster_secondary_range_name  = "pod-ranges"
    services_secondary_range_name = "services-range"
    #google_compute_subnetwork.subnet.secondary_ip_range[0].range_name
  }

}

# Separately Managed Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = google_container_cluster.primary.name
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gke_num_nodes
  # Limit IP address usage for now. If max_pods_per_node is too high,
  # (eg the default of 100+) we use up all the space in the pod-ranges
  # IP allocation and the cluster won't start.
  max_pods_per_node = 20

  node_config {
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]

    labels = {
      env = var.project_id
    }

    # Get a discount by allowing nodes to be yanked by GCE at a moment's notice.
    preemptible = true
    # Make sure we use a machine type which is available in the target cluster.
    machine_type = "e2-standard-2"
    # Amusingly, the default example provided by hashicorp for using terraform
    # with GKE exceeds available SSD quota on a trial account.
    # I got this running by specifying a non-SSD disk_type and limiting disk
    # size to 50GB. Since it can take 30+ mins (the timeout is 40 mins) for the
    # process to try and then not succeed (without helpfully failing early to
    # tell you to get more quota), I've stuck with the working combo.
    # In a real cluster, I'd make this more deterministic.
    disk_type       = "pd-standard"
    local_ssd_count = 0
    disk_size_gb    = 50
    tags            = ["gke-node", "${var.project_id}-gke"]
    metadata = {
      disable-legacy-endpoints = "true"
    }
  }

  autoscaling {
    min_node_count  = 0
    max_node_count  = 3
    location_policy = "ANY" # Not too worried about zone failures today
  }
}


# # Kubernetes provider
# # The Terraform Kubernetes Provider configuration below is used as a learning reference only. 
# # It references the variables and resources provisioned in this file. 
# # We recommend you put this in another file -- so you can have a more modular configuration.
# # https://learn.hashicorp.com/terraform/kubernetes/provision-gke-cluster#optional-configure-terraform-kubernetes-provider
# # To learn how to schedule deployments and services using the provider, go here: https://learn.hashicorp.com/tutorials/terraform/kubernetes-provider.

# provider "kubernetes" {
#   load_config_file = "false"

#   host     = google_container_cluster.primary.endpoint
#   username = var.gke_username
#   password = var.gke_password

#   client_certificate     = google_container_cluster.primary.master_auth.0.client_certificate
#   client_key             = google_container_cluster.primary.master_auth.0.client_key
#   cluster_ca_certificate = google_container_cluster.primary.master_auth.0.cluster_ca_certificate
# }

