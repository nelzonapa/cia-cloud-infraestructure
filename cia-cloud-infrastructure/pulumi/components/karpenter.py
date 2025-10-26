"""Módulo de Karpenter para auto-scaling automático de nodos."""
import pulumi
from pulumi_gcp import serviceaccount, projects
from pulumi_kubernetes import provider as kubernetes_provider
from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

def setup_karpenter(cluster, k8s_provider):
    """Configura Karpenter para auto-scaling automático de nodos."""
    
    config = pulumi.Config()
    project = config.require("project")
    
    # 1. CREAR UNA CUENTA DE SERVICIO PARA KARPENTER
    karpenter_service_account = serviceaccount.Account(
        "karpenter-service-account",
        account_id="karpenter-sa",
        display_name="Karpenter Service Account",
        description="Cuenta de servicio para Karpenter auto-scaling"
    )

    # 2. ASIGNAR ROLES IAM ESPECÍFICOS PARA KARPENTER
    # Rol: Administrar instancias de Compute Engine
    compute_instance_admin = projects.IAMMember(
        "karpenter-compute-instance-admin",
        project=project,
        role="roles/compute.instanceAdmin.v1",
        member=karpenter_service_account.email.apply(
            lambda email: f"serviceAccount:{email}"
        )
    )
    
    # Rol: Usar cuentas de servicio (para que Karpenter use la cuenta de los nodos)
    service_account_user = projects.IAMMember(
        "karpenter-service-account-user", 
        project=project,
        role="roles/iam.serviceAccountUser",
        member=karpenter_service_account.email.apply(
            lambda email: f"serviceAccount:{email}"
        )
    )


