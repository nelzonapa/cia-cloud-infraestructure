"""Módulo para desplegar la aplicación IoT en el cluster GKE."""
import pulumi
from pulumi_kubernetes.apps import v1 as apps_v1
from pulumi_kubernetes.core import v1 as core_v1
from pulumi_kubernetes.meta import v1 as meta_v1

import base64

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

    # 3. CREAR UN INGRESS PARA ACCESO EXTERNO (OPCIONAL)
    # Esto nos permitirá acceder a la aplicación desde fuera del cluster
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
            type="LoadBalancer"  # Google Cloud creará un Load Balancer automáticamente
        )
    )

    return {
        "deployment": deployment,
        "service": service,
        "ingress": ingress
    }
