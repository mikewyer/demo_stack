# Get helm installed on new GKE cluster

# CREDENTIALS:
# Run
# gcloud container clusters get-credentials lets-get-it-started-384609-gke --region europe-north1

variable "kube_context" {
  default     = ""
  description = "Which kubectl context to connect to"
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.kube_context
}

provider "helm" {
  # Helm could talk to a different kubernetes cluster if it wanted to.
  # TODO: find the best way to avoid this duplication.
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = var.kube_context
  }
}


resource "helm_release" "sock_shop" {
  name             = "sock-shop"
  chart            = "${path.module}/chart/sock-shop"
  namespace        = "sock-shop"
  create_namespace = true
  # It took about 6 minutes for the job to be healthy
  timeout = 900
}
