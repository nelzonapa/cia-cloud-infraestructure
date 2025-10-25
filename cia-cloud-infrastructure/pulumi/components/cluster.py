"""Módulo del cluster GKE para la infraestructura de CIA Cloud."""
import pulumi
from pulumi_gcp import container, serviceaccount, projects

def create_cluster(network):
    """Crea un cluster GKE con auto-scaling configurado."""
    
    config = pulumi.Config()
    project = config.require("project")
    region = config.require("region")
    
    # 1. CREAR UNA CUENTA DE SERVICIO PARA EL CLUSTER
    cluster_service_account = serviceaccount.Account(
        "cluster-service-account",
        account_id="cia-gke-sa",
        display_name="Service Account for CIA GKE Cluster",
        description="Cuenta de servicio para el cluster GKE de CIA Cloud"
    )

    # 2. ASIGNAR ROLES IAM A LA CUENTA DE SERVICIO
    # Rol: Editor de Compute Engine (para gestionar nodos)
    compute_editor = projects.IAMMember(
        "cluster-compute-editor",
        project=project,
        role="roles/compute.editor",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )
    
    # Rol: Viewer de Monitoring (para métricas de auto-scaling)
    monitoring_viewer = projects.IAMMember(
        "cluster-monitoring-viewer", 
        project=project,
        role="roles/monitoring.viewer",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )
    
    # Rol: Admin de Storage (para acceder a Cloud Storage)
    storage_admin = projects.IAMMember(
        "cluster-storage-admin",
        project=project,
        role="roles/storage.admin",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )