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
  kubernetes {
    config_path    = "~/.kube/config"
    config_context = var.kube_context
  }
}


resource "helm_release" "ingress-nginx" {
  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"

  namespace        = "ingress-nginx"
  create_namespace = true

  # switching from nginx as an ingress to nginx-operator,
  # don't think we need values.
  #   values = [
  #     file("${path.module}/chart/nginx/values.yaml")
  #   ]
}

data "kubernetes_service" "ingress-nginx" {
  depends_on = [helm_release.ingress-nginx]
  metadata {
    name      = "ingress-nginx-controller"
    namespace = "ingress-nginx"
  }
}

output "nginx_endpoint" {
  value = "http://${data.kubernetes_service.ingress-nginx.status.0.load_balancer.0.ingress.0.ip}/"
}
