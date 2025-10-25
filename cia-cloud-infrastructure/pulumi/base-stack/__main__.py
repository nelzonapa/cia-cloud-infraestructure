import pulumi
from components import networking

# Crear la infraestructura de red
network = networking.create_network()

# Exportar información importante para referencia
pulumi.export("vpc_name", network["vpc"].name)
pulumi.export("subnet_name", network["subnet"].name)
pulumi.export("subnet_region", network["subnet"].region)
pulumi.export("vpc_id", network["vpc"].id)