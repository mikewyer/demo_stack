variable "project_id" {
  description = "project id"
}

variable "region" {
  description = "region"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC
resource "google_compute_network" "vpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = "false"
}

# Subnet - using secondary_ip_ranges on hint from
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/using_gke_with_terraform#vpc-native-clusters
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_id}-subnet"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.10.0.0/24"

  secondary_ip_range {
    ip_cidr_range = "192.168.1.0/25"
    range_name    = "services-range"
  }

  secondary_ip_range {
    ip_cidr_range = "192.168.64.0/22"
    range_name    = "pod-ranges"
  }

}
