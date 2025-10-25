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


    # 3. CREAR EL CLUSTER GKE
    cluster = container.Cluster(
        "autoscale-cluster",
        name="autoscale-cluster",
        description="Cluster GKE para autoscaling con Karpenter",
        location=region,  # Usar región (cluster regional)
        initial_node_count=1,  # Un nodo inicial
        
        # Configuración de red
        network=network["vpc"].name,
        subnetwork=network["subnet"].name,
        
        # Configuración de IPs privadas (más seguro)
        private_cluster_config={
            "enable_private_nodes": True,
            "enable_private_endpoint": False,  # Permitir acceso público al endpoint
            "master_ipv4_cidr_block": "172.16.0.0/28"
        },
        
        # Configuración del node pool por defecto (mínimo)
        node_config={
            "service_account": cluster_service_account.email,
            "oauth_scopes": [
                "https://www.googleapis.com/auth/cloud-platform"
            ],
            "machine_type": "e2-small",  # Máquina económica para inicio
            "disk_size_gb": 20,
            "disk_type": "pd-standard",
        },
        
        # Habilitar auto-scaling del control plane
        enable_autopilot=False,  # Usamos modo estándar para más control
        
        # Configuración de mantenimiento
        maintenance_policy={
            "daily_maintenance_window": {
                "start_time": "03:00"  # Ventana de mantenimiento a las 3 AM
            }
        },
        
        # Habilitar características necesarias para Karpenter
        addons_config={
            "horizontal_pod_autoscaling": {
                "disabled": False
            },
            "http_load_balancing": {
                "disabled": False
            }
        },
        
        # Configuración de la versión
        release_channel={
            "channel": "REGULAR"  # Canal estable
        },
        
        # Resource limits para el control plane
        resource_limits={
            "resource_type": "cpu",
            "minimum": "1",
            "maximum": "2"
        },
        {
            "resource_type": "memory", 
            "minimum": "2GB",
            "maximum": "4GB"
        }
    )