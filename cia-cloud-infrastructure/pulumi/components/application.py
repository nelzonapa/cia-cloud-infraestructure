"""Módulo para desplegar la aplicación IoT en el cluster GKE."""
import pulumi
from pulumi_kubernetes.apps import v1 as apps_v1
from pulumi_kubernetes.core import v1 as core_v1
from pulumi_kubernetes.meta import v1 as meta_v1
from pulumi_kubernetes.rbac import v1 as rbac_v1

def deploy_iot_application(cluster):
    """Despliega la aplicación IoT Processor en el cluster GKE."""
    
    # Configuración
    app_name = "iot-processor"
    image = "gcr.io/cia-cloud-project/iot-processor:latest"
    
    # 1. CREAR DEPLOYMENT DE LA APLICACIÓN
    deployment = apps_v1.Deployment(
        f"{app_name}-deployment",
        metadata=meta_v1.ObjectMetaArgs(
            name=app_name,
            namespace="default",
            labels={
                "app": app_name,
                "version": "v1"
            }
        ),
        spec=apps_v1.DeploymentSpecArgs(
            replicas=2,  # Iniciamos con 2 réplicas
            selector=meta_v1.LabelSelectorArgs(
                match_labels={
                    "app": app_name
                }
            ),
            template=core_v1.PodTemplateSpecArgs(
                metadata=meta_v1.ObjectMetaArgs(
                    labels={
                        "app": app_name
                    },
                    annotations={
                        "prometheus.io/scrape": "true",
                        "prometheus.io/port": "8080",
                        "prometheus.io/path": "/metrics"
                    }
                ),
                spec=core_v1.PodSpecArgs(
                    containers=[
                        core_v1.ContainerArgs(
                            name=app_name,
                            image=image,
                            ports=[core_v1.ContainerPortArgs(container_port=8080)],
                            env=[
                                core_v1.EnvVarArgs(
                                    name="PYTHONUNBUFFERED",
                                    value="1"
                                )
                            ],
                            resources=core_v1.ResourceRequirementsArgs(
                                requests={
                                    "cpu": "100m",
                                    "memory": "128Mi"
                                },
                                limits={
                                    "cpu": "500m",
                                    "memory": "256Mi"
                                }
                            ),
                            liveness_probe=core_v1.ProbeArgs(
                                http_get=core_v1.HTTPGetActionArgs(
                                    path="/health",
                                    port=8080
                                ),
                                initial_delay_seconds=30,
                                period_seconds=10,
                                timeout_seconds=5
                            ),
                            readiness_probe=core_v1.ProbeArgs(
                                http_get=core_v1.HTTPGetActionArgs(
                                    path="/health", 
                                    port=8080
                                ),
                                initial_delay_seconds=5,
                                period_seconds=5,
                                timeout_seconds=3
                            )
                        )
                    ]
                )
            )
        )
    )

    # 2. CREAR SERVICE PARA LA APLICACIÓN
    service = core_v1.Service(
        f"{app_name}-service",
        metadata=meta_v1.ObjectMetaArgs(
            name=f"{app_name}-service",
            namespace="default",
            labels={
                "app": app_name
            }
        ),
        spec=core_v1.ServiceSpecArgs(
            selector={
                "app": app_name
            },
            ports=[
                core_v1.ServicePortArgs(
                    name="http",
                    port=80,
                    target_port=8080
                )
            ],
            type="ClusterIP"
        )
    )

    # 3. CREAR LOAD BALANCER PARA ACCESO EXTERNO
    ingress = core_v1.Service(
        f"{app_name}-loadbalancer",
        metadata=meta_v1.ObjectMetaArgs(
            name=f"{app_name}-loadbalancer",
            namespace="default",
        ),
        spec=core_v1.ServiceSpecArgs(
            selector={
                "app": app_name
            },
            ports=[
                core_v1.ServicePortArgs(
                    port=80,
                    target_port=8080
                )
            ],
            type="LoadBalancer"
        )
    )

    return {
        "deployment": deployment,
        "service": service,
        "ingress": ingress
    }

def deploy_custom_autoscaler(cluster):
    """Despliega el controlador de auto-scaling personalizado."""
    
    # Crear Service Account para el autoscaler
    autoscaler_sa = core_v1.ServiceAccount(
        "custom-autoscaler-sa",
        metadata=meta_v1.ObjectMetaArgs(
            name="custom-autoscaler-sa",
            namespace="default",
        )
    )
    
    # Crear ClusterRole y ClusterRoleBinding para permisos
    cluster_role = rbac_v1.ClusterRole(
        "custom-autoscaler-role",
        metadata=meta_v1.ObjectMetaArgs(
            name="custom-autoscaler-role",
        ),
        rules=[
            rbac_v1.PolicyRuleArgs(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=["get", "list", "watch", "patch"]
            ),
            rbac_v1.PolicyRuleArgs(
                api_groups=[""],
                resources=["pods", "services"],
                verbs=["get", "list"]
            )
        ]
    )
    
    cluster_role_binding = rbac_v1.ClusterRoleBinding(
        "custom-autoscaler-binding",
        metadata=meta_v1.ObjectMetaArgs(
            name="custom-autoscaler-binding",
        ),
        subjects=[rbac_v1.SubjectArgs(
            kind="ServiceAccount",
            name="custom-autoscaler-sa",
            namespace="default"
        )],
        role_ref=rbac_v1.RoleRefArgs(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name="custom-autoscaler-role"
        )
    )
    
    # Deployment del autoscaler
    autoscaler_deployment = apps_v1.Deployment(
        "custom-autoscaler",
        metadata=meta_v1.ObjectMetaArgs(
            name="custom-autoscaler",
            namespace="default",
            labels={
                "app": "custom-autoscaler",
                "component": "autoscaling"
            }
        ),
        spec=apps_v1.DeploymentSpecArgs(
            replicas=1,
            selector=meta_v1.LabelSelectorArgs(
                match_labels={
                    "app": "custom-autoscaler"
                }
            ),
            template=core_v1.PodTemplateSpecArgs(
                metadata=meta_v1.ObjectMetaArgs(
                    labels={
                        "app": "custom-autoscaler"
                    }
                ),
                spec=core_v1.PodSpecArgs(
                    service_account_name="custom-autoscaler-sa",
                    containers=[
                        core_v1.ContainerArgs(
                            name="autoscaler",
                            image="gcr.io/cia-cloud-project/custom-autoscaler:latest",
                            env=[
                                core_v1.EnvVarArgs(
                                    name="PYTHONUNBUFFERED",
                                    value="1"
                                )
                            ],
                            resources=core_v1.ResourceRequirementsArgs(
                                requests={
                                    "cpu": "100m",
                                    "memory": "128Mi"
                                },
                                limits={
                                    "cpu": "200m", 
                                    "memory": "256Mi"
                                }
                            )
                        )
                    ]
                )
            )
        )
    )
    
    return {
        "deployment": autoscaler_deployment,
        "service_account": autoscaler_sa,
        "cluster_role": cluster_role,
        "cluster_role_binding": cluster_role_binding
    }