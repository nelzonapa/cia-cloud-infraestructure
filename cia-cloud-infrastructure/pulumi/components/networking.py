"""Módulo de redes para la infraestructura de CIA Cloud."""
import pulumi
from pulumi_gcp import compute

def create_network():
    """Crea la infraestructura de red: VPC, subred, firewall y NAT."""
    # Configuración
    config = pulumi.Config() # lee configuración, obtiene lo mismo del comando "pulumi config"
    project = config.require("project") #id proyecto
    region = config.require("region") #region de proyecto

    # 1. CREAR LA VPC (RED PRINCIPAL)
    """
    1. compute.Network() - Crea una VPC en Google Cloud
    2. "main-vpc" - Nombre lógico en Pulumi (para referencia interna)
    3. name="main-vpc" - Nombre real en Google Cloud
    4. auto_create_subnetworks=False - IMPORTANTE: Desactivamos subredes automáticas para tener control total
    5. routing_mode="REGIONAL" - El routing funciona dentro de la región
    """
    main_vpc = compute.Network(
        "main-vpc",
        name="main-vpc",
        description="VPC principal para el cluster de autoscaling",
        auto_create_subnetworks=False,
        routing_mode="REGIONAL"
    )



    # 2. CREAR LA SUBNET (SUBRED PRINCIPAL)
    main_subnet = compute.Subnetwork(
        "main-subnet",
        name="main-subnet",
        description="Subred principal para el cluster GKE",
        network=main_vpc.id, # Conecta esta subred con la VPC principal
        region=region, # Región donde se creará la subred
        # Rango de IPs privadas para la subred
        ip_cidr_range="10.0.0.0/16",
        # Habilitar IPs privadas para los nodos (GKE requiere esto)
        private_ip_google_access=True,
        # Aquí guardamos registros logging
        log_config=compute.SubnetworkLogConfigArgs(
            aggregation_interval="INTERVAL_5_SEC",
            flow_sampling=0.5,
            metadata="INCLUDE_ALL_METADATA"
        )
    )