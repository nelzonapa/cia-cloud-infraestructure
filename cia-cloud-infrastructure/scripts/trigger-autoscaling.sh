#!/bin/bash
# Disparador optimizado de autoscaling

echo "=== DISPARADOR DE AUTOSCALING ==="
echo "Iniciando prueba de escalado..."

# Función para verificar si hay pods pendientes
check_pending_pods() {
    local pending_count=$(kubectl get pods | grep stress-test | grep -c Pending)
    echo "Pods pendientes: $pending_count"
    [ $pending_count -gt 0 ]
}

# Escalado agresivo para forzar autoscaling
echo "Fase 1: 15 réplicas (forzar escalado)"
kubectl scale deployment cpu-stress-test --replicas=15
echo "Esperando a que se desplieguen pods..."
sleep 30

# Verificar si se necesitan más nodos
if check_pending_pods; then
    echo "¡Hay pods pendientes! El autoscaler debería agregar nodos..."
    echo "Monitorea en la otra terminal..."
fi

echo "Fase 2: 25 réplicas (máxima presión)"
kubectl scale deployment cpu-stress-test --replicas=25
sleep 45

echo "Fase 3: Observar recuperación (10 réplicas)"
kubectl scale deployment cpu-stress-test --replicas=10
sleep 60

echo "Fase 4: Limpieza (1 réplica)"
kubectl scale deployment cpu-stress-test --replicas=1

echo "Prueba completada. El cluster debería escalar hacia abajo en los próximos minutos."