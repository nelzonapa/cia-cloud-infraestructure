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