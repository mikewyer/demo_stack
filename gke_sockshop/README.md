# GKE SockShop

More involved scenario using terraform to create and populate a GKE cluster.

Uses helm, kube-prometheus-stack, and https://microservices-demo.github.io/ as a
real workload.

## Getting started

This project uses gcloud default auth to avoid needing certs / passwords all
over the place.

Under the `terraform/` directory there are numbered layers:

- 0infra - VPC (network setup), GKE cluster, one managed node_pool
- 1kube - Basic cluster services- helm, an ingress-nginx instance
- 2monitor - Cluster default monitoring and alerting using kube-prometheus-stack
  via helm
- 3sockshop - The sockshop microservice demo app, deployed via helm

Terraform works best when it only operates on collections of objects with a
shared fate, or lifecycle status. That's configured as a separate directory /
module with its own terraform state.

The cluster is (hopefully) long-lived, and somewhat independent of the services
that run on it. As long as the cluster is there, that's all the higher layers of
the stack need to know. And we can safely start, stop, update, or replace the
running services without risking shutting down the cluster by mistake.

In this example, we create a single cluster and (manually) give it a kubectl
context name of `gke-default`. In a production scenario, you would probably have
multiple clusters with similar configs deployed to other regions (for lower
latency and higher redundancy/availability).

We would want to support a per-cluster override of some config values (replica
counts, machine type, supported host names) while keeping everything else
consistent.
