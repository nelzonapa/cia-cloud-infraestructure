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


    # 5. CREAR UN PROVISIONER (define CÓMO Karpenter crea nodos)
    provisioner = pulumi_kubernetes.apiextensions.CustomResource(
        "karpenter-provisioner",
        api_version="karpenter.sh/v1alpha5",
        kind="Provisioner",
        metadata={
            "name": "default",
            "namespace": "karpenter",
        },
        spec={
            "requirements": [
                {
                    "key": "node.kubernetes.io/instance-type",
                    "operator": "In",
                    "values": ["e2-small", "e2-medium", "e2-standard-2"]
                },
                {
                    "key": "topology.kubernetes.io/zone", 
                    "operator": "In",
                    "values": ["us-central1-a", "us-central1-b", "us-central1-c"]
                }
            ],
            "limits": {
                "resources": {
                    "cpu": 100,  # Máximo 100 CPUs en total
                    "memory": "100Gi"  # Máximo 100GB de memoria
                }
            },
            "providerRef": {
                "name": "default"
            },
            "ttlSecondsAfterEmpty": 30,  # Eliminar nodos después de 30 segundos vacíos
            "ttlSecondsUntilExpired": 604800,  # Rotar nodos después de 7 días
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[karpenter_release])
    )

    # Retornar los recursos creados
    return {
        "service_account": karpenter_service_account,
        "karpenter_release": karpenter_release,
        "provisioner": provisioner
    }