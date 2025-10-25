import pulumi
from components import networking, cluster 

# Crear la infraestructura de red
network = networking.create_network()

# Crear el cluster GKE
gke_cluster = cluster.create_cluster(network)

# Exportar información importante para referencia
pulumi.export("vpc_name", network["vpc"].name)
pulumi.export("subnet_name", network["subnet"].name)
pulumi.export("subnet_region", network["subnet"].region)
pulumi.export("vpc_id", network["vpc"].id)
# nuevo
pulumi.export("cluster_name", gke_cluster["cluster"].name)
pulumi.export("cluster_endpoint", gke_cluster["cluster"].endpoint)