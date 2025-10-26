"""Módulo de redes para la infraestructura de CIA Cloud."""
import pulumi
from pulumi_gcp import compute

def create_network():
    """Crea la infraestructura de red: VPC, subred, firewall y NAT."""
    # Configuración
    # config = pulumi.Config() # lee configuración, obtiene lo mismo del comando "pulumi config"
    from pulumi_gcp import config as gcp_config
    #project = config.require("project") #id proyecto
    project = gcp_config.project
    #region = config.require("region") #region de proyecto
    region = gcp_config.region

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

    # 3. CREAR REGLAS DE FIREWALL
    # Regla: Permitir tráfico interno entre nodos del cluster
    internal_traffic = compute.Firewall(
        "allow-internal-traffic",
        name="allow-internal-traffic",
        description="Permitir tráfico interno entre nodos del cluster",
        network=main_vpc.id,
        # Permitir todo el tráfico dentro de la VPC
        source_ranges=["10.0.0.0/16"],
        allows=[
            compute.FirewallAllowArgs(
                protocol="tcp",
                ports=["0-65535"]  # Todos los puertos TCP
            ),
            compute.FirewallAllowArgs(
                protocol="udp", 
                ports=["0-65535"]  # Todos los puertos UDP
            ),
            compute.FirewallAllowArgs(
                protocol="icmp"  # Para ping/diagnóstico
            )
        ]
    )

    # Regla: Permitir tráfico SSH para administración
    ssh_traffic = compute.Firewall(
        "allow-ssh",
        name="allow-ssh",
        description="Permitir conexiones SSH para administración",
        network=main_vpc.id,
        source_ranges=["0.0.0.0/0"],  # Desde cualquier lugar (¡cuidado en producción!)
        allows=[
            compute.FirewallAllowArgs(
                protocol="tcp",
                ports=["22"]  # Solo puerto SSH
            )
        ]
    )


    # Regla: Permitir tráfico HTTP y HTTPS desde internet
    web_traffic = compute.Firewall(
        "allow-web-traffic",
        name="allow-web-traffic",
        description="Permitir tráfico HTTP y HTTPS desde internet",
        network=main_vpc.id,
        source_ranges=["0.0.0.0/0"],  # Desde cualquier lugar
        allows=[
            compute.FirewallAllowArgs(
                protocol="tcp",
                ports=["80", "443"]  # HTTP y HTTPS
            )
        ]
    )

    # Regla: Permitir puertos específicos para el servidor Ubiq
    ubiq_traffic = compute.Firewall(
        "allow-ubiq-traffic",
        name="allow-ubiq-traffic",
        description="Permitir tráfico para servidor Ubiq (MetaQuest)",
        network=main_vpc.id,
        source_ranges=["0.0.0.0/0"],
        allows=[
            compute.FirewallAllowArgs(
                protocol="tcp",
                ports=["8009", "8010", "8011"]  # Puertos del servidor Ubiq
            )
        ]
    )


    # 4. CREAR CLOUD NAT PARA CONECTIVIDAD SALIENTE
    # Primero, creamos un router para el NAT
    nat_router = compute.Router(
        "nat-router",
        name="nat-router",
        description="Router para Cloud NAT",
        network=main_vpc.id,
        region=region
    )

    # Luego, creamos el Cloud NAT
    cloud_nat = compute.RouterNat(
        "cloud-nat",
        name="cloud-nat",
        router=nat_router.name,
        region=region,
        # Configurar el NAT para usar IPs automáticas
        nat_ip_allocate_option="AUTO_ONLY",
        # Habilitar NAT para todas las subredes
        source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    )

    # Retornar todos los recursos creados para que otros módulos los usen
    return {
        "vpc": main_vpc,
        "subnet": main_subnet,
        "internal_firewall": internal_traffic,
        "ssh_firewall": ssh_traffic,
        "web_firewall": web_traffic,
        "ubiq_firewall": ubiq_traffic,
        "nat_router": nat_router,
        "cloud_nat": cloud_nat
    }