#!/usr/bin/env python3
"""
Script para generar carga en la aplicación IoT y activar el auto-scaling.
"""
import requests
import time
import random
import threading
import sys
from concurrent.futures import ThreadPoolExecutor

def get_app_url():
    """Obtiene la URL de la aplicación desde Kubernetes"""
    try:
        import subprocess
        result = subprocess.run([
            'kubectl', 'get', 'service', 'iot-processor-loadbalancer',
            '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return f"http://{result.stdout.strip()}"
        else:
            return "http://34.171.250.213"  # Tu IP actual
    except:
        return "http://34.171.250.213"

APP_URL = get_app_url()

def send_sensor_data(sensor_id, num_requests):
    """Envía datos de sensores sintéticos a la aplicación"""
    successful_requests = 0
    
    for i in range(num_requests):
        try:
            # Generar datos de sensor realistas
            sensor_data = {
                "sensor_id": f"sensor_{sensor_id}_{i:04d}",
                "temperature": round(random.uniform(15.0, 35.0), 2),
                "humidity": round(random.uniform(30.0, 80.0), 2),
                "pressure": round(random.uniform(1000.0, 1020.0), 2),
                "timestamp": time.time()
            }
            
            # Enviar datos a la aplicación
            response = requests.post(
                f"{APP_URL}/sensor-data",
                json=sensor_data,
                timeout=10
            )
            
            if response.status_code == 200:
                successful_requests += 1
                result = response.json()
                if result.get('status') == 'processed':
                    print(f"✅ Sensor {sensor_id}: Lote procesado - {result.get('batch_result', {})}")
                else:
                    print(f"⏳ Sensor {sensor_id}: En cola - posición {result.get('queue_position', '?')}")
            else:
                print(f"❌ Sensor {sensor_id}: Error HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"🌐 Sensor {sensor_id}: Error de conexión - {e}")
        except Exception as e:
            print(f"💥 Sensor {sensor_id}: Error inesperado - {e}")
        
        # Pequeña pausa entre requests
        time.sleep(random.uniform(0.1, 0.5))
    
    return successful_requests

def stress_test():
    """Ejecuta prueba de carga masiva usando el endpoint de stress-test"""
    try:
        print("🚀 Iniciando prueba de carga masiva...")
        response = requests.post(
            f"{APP_URL}/stress-test",
            json={"batch_size": 50},  # Generar 50 datos sintéticos de una vez
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Carga masiva generada: {result}")
            return True
        else:
            print(f"❌ Error en carga masiva: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"💥 Error en carga masiva: {e}")
        return False

def monitor_application():
    """Monitorea el estado de la aplicación durante la prueba"""
    while True:
        try:
            # Obtener estado actual
            response = requests.get(f"{APP_URL}/sensor-data", timeout=5)
            if response.status_code == 200:
                status = response.json()
                print(f"📊 Estado - Procesados: {status.get('total_processed', 0)}, Cola: {status.get('queue_size', 0)}")
            
            # Obtener métricas
            metrics_response = requests.get(f"{APP_URL}/metrics", timeout=5)
            if metrics_response.status_code == 200:
                for line in metrics_response.text.split('\n'):
                    if 'processing_queue_size' in line:
                        print(f"📈 Métrica cola: {line.strip()}")
                    elif 'active_requests' in line:
                        print(f"🔥 Requests activas: {line.strip()}")
            
            time.sleep(10)  # Monitorear cada 10 segundos
            
        except Exception as e:
            print(f"📡 Error monitoreando: {e}")
            time.sleep(30)

def main():
    """Función principal"""
    print("🎯 INICIANDO PRUEBA DE AUTO-SCALING")
    print("=" * 50)
    print(f"🔗 Aplicación: {APP_URL}")
    
    # Verificar que la aplicación esté funcionando
    try:
        health_response = requests.get(f"{APP_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Aplicación IoT está saludable")
        else:
            print("❌ La aplicación no responde correctamente")
            return
    except Exception as e:
        print(f"❌ No se puede conectar a la aplicación: {e}")
        return
    
    # Iniciar monitoreo en segundo plano
    import threading
    monitor_thread = threading.Thread(target=monitor_application, daemon=True)
    monitor_thread.start()
    
    # Fase 1: Carga gradual
    print("\n📈 FASE 1: Carga gradual (10 sensores)")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(10):
            future = executor.submit(send_sensor_data, i, 20)  # 20 requests por sensor
            futures.append(future)
        
        total_successful = sum(f.result() for f in futures)
        print(f"✅ Fase 1 completada: {total_successful} requests exitosas")
    
    time.sleep(10)  # Esperar a que el sistema se estabilice
    
    # Fase 2: Carga masiva
    print("\n🔥 FASE 2: Carga masiva")
    for _ in range(5):  # 5 rondas de carga masiva
        if stress_test():
            time.sleep(15)  # Esperar entre rondas
        else:
            break
    
    # Fase 3: Carga sostenida
    print("\n🏃 FASE 3: Carga sostenida (20 sensores)")
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(10, 30):  # 20 sensores más
            future = executor.submit(send_sensor_data, i, 30)  # 30 requests por sensor
            futures.append(future)
        
        total_successful = sum(f.result() for f in futures)
        print(f"✅ Fase 3 completada: {total_successful} requests exitosas")
    
    print("\n🎉 PRUEBA COMPLETADA")
    print("📊 Revisa los logs del autoscaler para ver las decisiones de escalado:")
    print("   kubectl logs -l app=custom-autoscaler --tail=50")

if __name__ == "__main__":
    main()
