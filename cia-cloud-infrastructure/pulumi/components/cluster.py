"""Módulo del cluster GKE para la infraestructura de CIA Cloud."""
import pulumi
from pulumi_gcp import container, serviceaccount, projects

def create_cluster(network):
    """Crea un cluster GKE zonal sin auto-scaling nativo de GKE."""
    
    from pulumi_gcp import config as gcp_config
    project = gcp_config.project
    region = gcp_config.region
    zone = "us-central1-a"  # Zona específica
    
    # 1. CREAR CUENTA DE SERVICIO PARA EL CLUSTER
    cluster_service_account = serviceaccount.Account(
        "cluster-service-account",
        account_id="cia-gke-sa",
        display_name="Service Account for CIA GKE Cluster",
        description="Cuenta de servicio para el cluster GKE de CIA Cloud"
    )

    # 2. ASIGNAR ROLES IAM A LA CUENTA DE SERVICIO
    compute_editor = projects.IAMMember(
        "cluster-compute-editor",
        project=project,
        role="roles/compute.instanceAdmin.v1",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )
    
    monitoring_viewer = projects.IAMMember(
        "cluster-monitoring-viewer", 
        project=project,
        role="roles/monitoring.viewer",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )
    
    storage_admin = projects.IAMMember(
        "cluster-storage-admin",
        project=project,
        role="roles/storage.admin",
        member=cluster_service_account.email.apply(lambda email: f"serviceAccount:{email}")
    )

    # 3. CREAR EL CLUSTER GKE ZONAL
    cluster = container.Cluster(
        "autoscale-cluster",
        name="autoscale-cluster",
        description="Cluster GKE zonal para autoscaling personalizado",
        location=zone,  # ✅ ZONA ESPECÍFICA, NO REGIÓN
        initial_node_count=1,

        deletion_protection=False,
        
        # ✅ ELIMINAR NODE POOL POR DEFECTO - USAREMOS NUESTRO PROPIO
        remove_default_node_pool=True,
        
        # Configuración de red
        network=network["vpc"].name,
        subnetwork=network["subnet"].name,
        
        # Configuración de IPs privadas
        private_cluster_config={
            "enable_private_nodes": True,
            "enable_private_endpoint": False,
            "master_ipv4_cidr_block": "172.16.0.0/28"
        },
        
        # MODO ESTÁNDAR PARA CONTROL TOTAL. Omitimos 'enable_autopilot=False' para resolver el conflicto.
        
        # Configuración de mantenimiento
        maintenance_policy={
            "daily_maintenance_window": {
                "start_time": "03:00"
            }
        },
        
        # Habilitar características para nuestro auto-scaling
        addons_config={
            "horizontal_pod_autoscaling": {
                "disabled": False  # ✅ Para nuestro HPA personalizado
            },
            "http_load_balancing": {
                "disabled": False
            }
        },
        
        # Configuración de la versión
        release_channel={
            "channel": "REGULAR"
        },
    )

    # 4. CREAR NODE POOL BÁSICO SIN AUTO-SCALING DE GKE
    node_pool = container.NodePool(
        "main-node-pool",
        name="main-node-pool",
        cluster=cluster.name,
        location=zone,  # ✅ MISMA ZONA QUE EL CLUSTER
        # initial_node_count=1, # ❌ Eliminado para evitar conflicto con node_count
        node_count=1,  # ✅ NÚMERO FIJO - SIN AUTO-SCALING DE GKE
        
        node_config={
            "preemptible": True,
            "machine_type": "e2-small",
            "disk_size_gb": 20,
            "disk_type": "pd-standard",
            "service_account": cluster_service_account.email,
            "oauth_scopes": [
                "https://www.googleapis.com/auth/cloud-platform"
            ],
            "labels": {
                "workload": "default"
            },
            "tags": ["gke-node", "cia-project"]
        },
        
        # ✅ SOLO MANTENIMIENTO AUTOMÁTICO, NO AUTO-SCALING
        management={
            "auto_repair": True,
            "auto_upgrade": True
        }
        
        # ❌ NO INCLUIR SECCIÓN autoscaling - LO MANEJAREMOS NOSOTROS
    )

    # Retornar los recursos creados
    return {
        "cluster": cluster,
        "node_pool": node_pool,
        "service_account": cluster_service_account
    }
