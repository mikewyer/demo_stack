# Add monitoring to our shiny new cluster

# CREDENTIALS:
# Run
# gcloud container clusters get-credentials lets-get-it-started-384609-gke --region europe-north1
# kubectl config rename-context gke_lets-get-it-started-384609_europe-north1_lets-get-it-started-384609-gke gke-default

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


resource "helm_release" "prometheus-stack" {
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "mon"
  create_namespace = true
}
