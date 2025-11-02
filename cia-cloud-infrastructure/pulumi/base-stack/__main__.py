import pulumi
import sys
import os

# Añadir el directorio padre al path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

# Imports
from pulumi_kubernetes import provider as kubernetes_provider
from components import networking, cluster, application

# Crear la infraestructura de red
network = networking.create_network()

# Crear el cluster GKE (con autoscaling nativo)
gke_cluster = cluster.create_cluster(network)


# Desplegar la aplicación IoT
iot_app = application.deploy_iot_application(gke_cluster)

# ----------------------------------------------------------------------
# CONFIGURAR PROVEEDOR DE KUBERNETES
# ----------------------------------------------------------------------
from pulumi_gcp import config as gcp_config

k8s_provider = kubernetes_provider.Provider(
    "k8s-provider",
    kubeconfig=pulumi.Output.all(
        gke_cluster["cluster"].name,
        gke_cluster["cluster"].endpoint,
        gke_cluster["cluster"].master_auth.cluster_ca_certificate,
        gcp_config.project,
        gcp_config.region
    ).apply(lambda args: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[2]}
    server: https://{args[1]}
  name: {args[0]}
contexts:
- context:
    cluster: {args[0]}
    user: {args[0]}
  name: {args[0]}
current-context: {args[0]}
kind: Config
preferences: {{}}
users:
- name: {args[0]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      provideClusterInfo: true
"""),
    opts=pulumi.ResourceOptions(depends_on=[gke_cluster["cluster"]])
)

# ----------------------------------------------------------------------
# EXPORTAR INFORMACIÓN
# ----------------------------------------------------------------------
pulumi.export("vpc_name", network["vpc"].name)
pulumi.export("subnet_name", network["subnet"].name)
pulumi.export("subnet_region", network["subnet"].region)
pulumi.export("vpc_id", network["vpc"].id)
pulumi.export("cluster_name", gke_cluster["cluster"].name)
pulumi.export("cluster_endpoint", gke_cluster["cluster"].endpoint)
pulumi.export("service_account", gke_cluster["service_account"].email)
pulumi.export("app_service", iot_app["service"].metadata["name"])
pulumi.export("loadbalancer_ip", iot_app["ingress"].status.apply(lambda s: s.load_balancer.ingress[0].ip if s.load_balancer.ingress else "Pending"))

# Comando para conectarse al cluster
pulumi.export("connect_command", pulumi.Output.concat(
    "gcloud container clusters get-credentials ",
    gke_cluster["cluster"].name,
    " --region=",
    network["subnet"].region,
    " --project=",
    gcp_config.project
))

# Información del autoscaling
pulumi.export("autoscaling_info", {
    "provider": "GKE Cluster Autoscaler (nativo)",
    "min_nodes": 1,
    "max_nodes": 3,
    "status": "Activado automáticamente"
})