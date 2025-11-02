#!/usr/bin/env python3
"""
Controlador de Auto-Scaling Personalizado para aplicación IoT.
Monitorea métricas personalizadas y ajusta el número de réplicas.
"""
import time
import logging
import requests
import json
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CustomAutoscaler:
    def __init__(self, app_name, namespace="default"):
        self.app_name = app_name
        self.namespace = namespace
        self.min_replicas = 1
        self.max_replicas = 5
        self.target_queue_size = 3  # Objetivo: mantener cola alrededor de 3 elementos
        
        # Configurar cliente Kubernetes
        try:
            config.load_incluster_config()  # Dentro del cluster
        except:
            config.load_kube_config()       # Para desarrollo local
        
        self.apps_v1 = client.AppsV1Api()

    def get_app_metrics(self):
        """Obtiene métricas de la aplicación IoT"""
        try:
            # Usar el servicio interno para obtener métricas
            service_url = f"http://iot-processor-service.default.svc.cluster.local"
            
            # Obtener métricas de Prometheus
            metrics_response = requests.get(f"{service_url}/metrics", timeout=5)
            metrics_data = {}
            
            if metrics_response.status_code == 200:
                for line in metrics_response.text.split('\n'):
                    if line.startswith('processing_queue_size'):
                        value = float(line.split()[1])
                        metrics_data['queue_size'] = value
                    elif line.startswith('active_requests'):
                        value = float(line.split()[1])
                        metrics_data['active_requests'] = value
            
            # Obtener estado actual de la aplicación
            status_response = requests.get(f"{service_url}/sensor-data", timeout=5)
            if status_response.status_code == 200:
                status_data = status_response.json()
                metrics_data['total_processed'] = status_data.get('total_processed', 0)
                metrics_data['current_queue'] = status_data.get('queue_size', 0)
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {'queue_size': 0, 'active_requests': 0, 'current_queue': 0}

    def get_current_replicas(self):
        """Obtiene el número actual de réplicas del deployment"""
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=self.app_name,
                namespace=self.namespace
            )
            return deployment.spec.replicas
        except ApiException as e:
            logger.error(f"Error obteniendo réplicas: {e}")
            return None

    def scale_deployment(self, new_replicas):
        """Escala el deployment al número especificado de réplicas"""
        try:
            if new_replicas < self.min_replicas:
                new_replicas = self.min_replicas
            elif new_replicas > self.max_replicas:
                new_replicas = self.max_replicas
            
            # Obtener deployment actual
            deployment = self.apps_v1.read_namespaced_deployment(
                name=self.app_name,
                namespace=self.namespace
            )
            
            current_replicas = deployment.spec.replicas
            
            if current_replicas != new_replicas:
                # Actualizar número de réplicas
                deployment.spec.replicas = new_replicas
                
                # Aplicar cambios
                self.apps_v1.patch_namespaced_deployment(
                    name=self.app_name,
                    namespace=self.namespace,
                    body=deployment
                )
                
                logger.info(f"🚀 Auto-scaling: {current_replicas} → {new_replicas} réplicas")
                return True
            else:
                logger.info(f"✅ Réplicas estables en {new_replicas}")
                return False
                
        except ApiException as e:
            logger.error(f"Error escalando deployment: {e}")
            return False

    def calculate_desired_replicas(self, metrics):
        """Calcula el número deseado de réplicas basado en las métricas"""
        current_replicas = self.get_current_replicas()
        if current_replicas is None:
            return self.min_replicas
        
        queue_size = metrics.get('queue_size', 0)
        current_queue = metrics.get('current_queue', 0)
        active_requests = metrics.get('active_requests', 0)
        
        logger.info(f"📊 Métricas - Cola: {queue_size}, Requests activas: {active_requests}")
        
        # Lógica de escalado personalizada
        desired_replicas = current_replicas
        
        # Escalar basado en el tamaño de la cola
        if queue_size > self.target_queue_size * 2:  # Cola muy grande
            desired_replicas = min(self.max_replicas, current_replicas + 2)
            logger.info(f"📈 Cola grande ({queue_size}), escalando agresivamente")
            
        elif queue_size > self.target_queue_size:  # Cola por encima del objetivo
            desired_replicas = min(self.max_replicas, current_replicas + 1)
            logger.info(f"📈 Cola creciendo ({queue_size}), escalando")
            
        elif queue_size < self.target_queue_size / 2 and current_replicas > self.min_replicas:  # Cola muy pequeña
            desired_replicas = max(self.min_replicas, current_replicas - 1)
            logger.info(f"📉 Cola pequeña ({queue_size}), reduciendo")
        
        # También considerar requests activas
        if active_requests > current_replicas * 3 and desired_replicas <= current_replicas:
            desired_replicas = min(self.max_replicas, current_replicas + 1)
            logger.info(f"🔥 Muchas requests activas ({active_requests}), escalando")
        
        return desired_replicas

    def run(self):
        """Bucle principal del autoscaler"""
        logger.info(f"🎯 Iniciando autoscaler personalizado para {self.app_name}")
        logger.info(f"📏 Configuración: Min={self.min_replicas}, Max={self.max_replicas}, TargetQueue={self.target_queue_size}")
        
        while True:
            try:
                # Obtener métricas
                metrics = self.get_app_metrics()
                
                # Calcular réplicas deseadas
                desired_replicas = self.calculate_desired_replicas(metrics)
                
                # Aplicar escalado si es necesario
                self.scale_deployment(desired_replicas)
                
                # Esperar antes de la siguiente iteración
                time.sleep(30)  # Revisar cada 30 segundos
                
            except Exception as e:
                logger.error(f"❌ Error en bucle principal: {e}")
                time.sleep(60)  # Esperar más en caso de error

if __name__ == "__main__":
    autoscaler = CustomAutoscaler(app_name="iot-processor")
    autoscaler.run()
