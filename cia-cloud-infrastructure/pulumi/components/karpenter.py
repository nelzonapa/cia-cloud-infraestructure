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

    # 3. CONFIGURAR WORKLOAD IDENTITY (para que Karpenter en Kubernetes use esta cuenta)
    workload_identity = projects.IAMMember(
        "karpenter-workload-identity",
        project=project,
        role="roles/iam.workloadIdentityUser",
        member=karpenter_service_account.email.apply(
            lambda email: f"serviceAccount:{project}.svc.id.goog[karpenter/karpenter]"
        )
    )


    # 4. INSTALAR KARPENTER USANDO HELM CHART
    karpenter_release = Release(
        "karpenter",
        ReleaseArgs(
            chart="karpenter",
            version="v0.36.1",  # Versión específica para estabilidad
            repository_opts=RepositoryOptsArgs(
                repo="https://charts.karpenter.sh"
            ),
            namespace="karpenter",
            create_namespace=True,
            values={
                "serviceAccount": {
                    "create": False,
                    "name": karpenter_service_account.account_id,
                    "annotations": {
                        "iam.gke.io/gcp-service-account": karpenter_service_account.email
                    }
                },
                "controller": {
                    "clusterName": cluster.name,
                    "clusterEndpoint": cluster.endpoint,
                },
                "aws": {}  # Karpenter soporta AWS, pero aquí lo deshabilitamos
            }
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[workload_identity])
    )
