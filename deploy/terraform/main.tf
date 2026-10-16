terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

resource "kubernetes_namespace" "ragops" {
  metadata {
    name = "ragops-${var.environment}"
    labels = {
      environment = var.environment
      managed_by  = "terraform"
    }
  }
}

resource "helm_release" "ragops" {
  name       = "ragops"
  repository = "deploy/helm"
  chart      = "."
  namespace  = kubernetes_namespace.ragops.metadata[0].name

  set {
    name  = "replicaCount"
    value = var.app_replicas
  }

  set {
    name  = "env.environment"
    value = var.environment
  }
}
