from flask import Flask, request, jsonify
import time
import random
import numpy as np
from prometheus_client import generate_latest, Counter, Histogram, Gauge
import json
import threading

app = Flask(__name__)

# Métricas para nuestro auto-scaling personalizado
REQUEST_COUNT = Counter('iot_requests_total', 'Total IoT data processing requests')
PROCESSING_TIME = Histogram('iot_processing_duration_seconds', 'IoT data processing duration')
CPU_LOAD = Gauge('cpu_load_percent', 'Simulated CPU load percentage')
ACTIVE_REQUESTS = Gauge('active_requests', 'Number of active processing requests')
QUEUE_SIZE = Gauge('processing_queue_size', 'Size of processing queue')

# Almacenamiento en memoria para datos IoT
sensor_data = []
processing_queue = []

def process_sensor_data_batch(data_batch):
    """
    Procesa un lote de datos IoT simulando análisis complejo.
    Esto consume CPU para demostrar el auto-scaling.
    """
    start_time = time.time()
    
    # Simular procesamiento intensivo de datos IoT
    # Análisis de patrones en datos de sensores
    temperatures = [sensor['temperature'] for sensor in data_batch]
    humidities = [sensor['humidity'] for sensor in data_batch]
    
    # Cálculos que consumen CPU
    if temperatures:
        # Análisis estadístico
        temp_array = np.array(temperatures)
        mean_temp = np.mean(temp_array)
        std_temp = np.std(temp_array)
        
        # Detección de anomalías (consumo CPU)
        anomalies = []
        for i, temp in enumerate(temperatures):
            if abs(temp - mean_temp) > 2 * std_temp:
                anomalies.append({
                    'sensor_id': data_batch[i]['sensor_id'],
                    'temperature': temp,
                    'deviation': temp - mean_temp
                })
        
        # Simular más procesamiento
        time.sleep(0.1)  # 100ms de procesamiento
        
        processing_time = time.time() - start_time
        CPU_LOAD.set(processing_time * 100)  # Convertir a porcentaje
        
        return {
            'batch_size': len(data_batch),
            'mean_temperature': mean_temp,
            'std_temperature': std_temp,
            'anomalies_detected': len(anomalies),
            'processing_time': processing_time
        }
    
    return {'batch_size': 0, 'processing_time': 0}

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud para Kubernetes"""
    return jsonify({
        "status": "healthy", 
        "service": "iot-data-processor",
        "timestamp": time.time(),
        "queue_size": len(processing_queue)
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Endpoint de métricas para Prometheus"""
    return generate_latest()

@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Recibe datos de sensores IoT y los procesa"""
    with PROCESSING_TIME.time():
        ACTIVE_REQUESTS.inc()
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Validar datos del sensor
            required_fields = ['sensor_id', 'temperature', 'humidity', 'timestamp']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing field: {field}"}), 400
            
            # Agregar a la cola de procesamiento
            processing_queue.append(data)
            QUEUE_SIZE.set(len(processing_queue))
            
            # Procesar en lotes de 5
            if len(processing_queue) >= 5:
                batch = processing_queue[:5]
                processing_queue[:5] = []  # Remover los procesados
                
                result = process_sensor_data_batch(batch)
                
                # Almacenar resultados
                sensor_data.extend(batch)
                if len(sensor_data) > 1000:  # Mantener solo últimos 1000
                    sensor_data[:] = sensor_data[-1000:]
                
                REQUEST_COUNT.inc()
                
                return jsonify({
                    "status": "processed",
                    "sensor_id": data['sensor_id'],
                    "batch_result": result,
                    "queue_remaining": len(processing_queue)
                })
            else:
                return jsonify({
                    "status": "queued", 
                    "sensor_id": data['sensor_id'],
                    "queue_position": len(processing_queue)
                })
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            ACTIVE_REQUESTS.dec()

@app.route('/sensor-data', methods=['GET'])
def get_sensor_data():
    """Obtiene datos de sensores procesados"""
    return jsonify({
        "total_processed": len(sensor_data),
        "queue_size": len(processing_queue),
        "recent_data": sensor_data[-10:] if sensor_data else []
    })

@app.route('/stress-test', methods=['POST'])
def stress_test():
    """Endpoint para pruebas de carga - genera datos IoT sintéticos"""
    batch_size = request.json.get('batch_size', 10)
    
    synthetic_data = []
    for i in range(batch_size):
        sensor_data = {
            'sensor_id': f"sensor_{random.randint(1000, 9999)}",
            'temperature': round(random.uniform(-10, 40), 2),
            'humidity': round(random.uniform(0, 100), 2),
            'pressure': round(random.uniform(900, 1100), 2),
            'timestamp': time.time()
        }
        processing_queue.append(sensor_data)
        synthetic_data.append(sensor_data)
    
    QUEUE_SIZE.set(len(processing_queue))
    
    return jsonify({
        "generated": batch_size,
        "total_queue": len(processing_queue)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
