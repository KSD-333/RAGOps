output "namespace" {
  description = "Deployed Kubernetes namespace"
  value       = kubernetes_namespace.ragops.metadata[0].name
}

output "helm_release_status" {
  description = "Status of the deployed Helm release"
  value       = helm_release.ragops.status
}
