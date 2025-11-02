#!/usr/bin/env python3
"""
Monitor en tiempo real del auto-scaling personalizado.
"""
import time
import subprocess
import json
import sys

def run_command(cmd):
    """Ejecuta un comando y retorna la salida"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Exception: {e}"

def get_deployment_status():
    """Obtiene el estado del deployment de IoT"""
    cmd = "kubectl get deployment iot-processor -o json"
    output = run_command(cmd)
    if output.startswith('{'):
        data = json.loads(output)
        return {
            'replicas': data['spec']['replicas'],
            'available': data['status'].get('availableReplicas', 0),
            'ready': data['status'].get('readyReplicas', 0)
        }
    return {'replicas': '?', 'available': '?', 'ready': '?'}

def get_pod_count():
    """Cuenta los pods de la aplicación"""
    cmd = "kubectl get pods -l app=iot-processor --no-headers | wc -l"
    return run_command(cmd)

def get_autoscaler_logs():
    """Obtiene los logs recientes del autoscaler"""
    cmd = "kubectl logs -l app=custom-autoscaler --tail=3 2>/dev/null || echo 'No logs available'"
    return run_command(cmd)

def get_node_usage():
    """Obtiene el uso de recursos de los nodos"""
    cmd = "kubectl top nodes 2>/dev/null || echo 'Metrics not available'"
    return run_command(cmd)

def clear_screen():
    """Limpia la pantalla"""
    print('\033[2J\033[H', end='')

def main():
    """Monitor principal"""
    print("🔍 Iniciando monitor de auto-scaling...")
    
    try:
        while True:
            clear_screen()
            print("🎯 MONITOR DE AUTO-SCALING PERSONALIZADO")
            print("=" * 60)
            
            # Estado del deployment
            deployment = get_deployment_status()
            print(f"\n📊 DEPLOYMENT IOT-PROCESSOR:")
            print(f"   • Réplicas deseadas: {deployment['replicas']}")
            print(f"   • Réplicas disponibles: {deployment['available']}")
            print(f"   • Réplicas listas: {deployment['ready']}")
            
            # Conteo de pods
            pod_count = get_pod_count()
            print(f"   • Pods totales: {pod_count}")
            
            # Uso de nodos
            node_usage = get_node_usage()
            print(f"\n🖥️  USO DE NODOS:")
            for line in node_usage.split('\n'):
                print(f"   • {line}")
            
            # Logs del autoscaler
            logs = get_autoscaler_logs()
            print(f"\n📝 ÚLTIMAS DECISIONES DEL AUTOSCALER:")
            for line in logs.split('\n'):
                if line.strip():
                    print(f"   • {line}")
            
            print(f"\n⏰ Actualizando en 10 segundos... (Ctrl+C para detener)")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitor detenido")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
