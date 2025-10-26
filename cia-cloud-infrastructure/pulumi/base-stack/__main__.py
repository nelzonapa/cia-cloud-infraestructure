import pulumi

import sys
import os

# AGREGAR ESTAS LÍNEAS AQUÍ:
# ----------------------------------------------------------------------
# Esto añade el directorio "pulumi" (el padre de base-stack) a la ruta de Python
# Permitiendo que las importaciones como "from components import..." funcionen.
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)
#Le dice al intérprete de Python: "Antes de que falles, mira también en esta ruta (/home/nelinux/.../pulumi) para encontrar los módulos que faltan."
# ----------------------------------------------------------------------


#imports
from pulumi_kubernetes import provider as kubernetes_provider

from components import networking, cluster, karpenter 

# Crear la infraestructura de red
network = networking.create_network()

# Crear el cluster GKE
gke_cluster = cluster.create_cluster(network)


# ----------------------------------------------------------------------
# LÓGICA DE KARPENTER Y KUBERNETES
# Configurar el proveedor de Kubernetes
# Usamos gke_cluster["cluster"].kubeconfig para la autenticación moderna de GKE
# Configurar el proveedor de Kubernetes (RESUELVE EL ERROR KEYERROR: 0)
# Provider de Kubernetes usando el CA directamente
# Provider de Kubernetes usando exec plugin gke-gcloud-auth-plugin
k8s_provider = kubernetes_provider.Provider(
    "k8s-provider",
    kubeconfig=pulumi.Output.all(
        gke_cluster["cluster"].name,
        gke_cluster["cluster"].endpoint,
        gke_cluster["cluster"].master_auth.cluster_ca_certificate
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
      apiVersion: client.authentication.k8s.io/v1
      command: gke-gcloud-auth-plugin
      args:
      - --format=json
""")
)


# Instalar Karpenter (asume que karpenter.py está completo y guardado)
karpenter_setup = karpenter.setup_karpenter(gke_cluster["cluster"], k8s_provider)

# ----------------------------------------------------------------------


# Exportar información importante para referencia
pulumi.export("vpc_name", network["vpc"].name)
pulumi.export("subnet_name", network["subnet"].name)
pulumi.export("subnet_region", network["subnet"].region)
pulumi.export("vpc_id", network["vpc"].id)
#cluster
pulumi.export("cluster_name", gke_cluster["cluster"].name)
pulumi.export("cluster_endpoint", gke_cluster["cluster"].endpoint)
#karpenter
pulumi.export("karpenter_service_account", karpenter_setup["service_account"].email)